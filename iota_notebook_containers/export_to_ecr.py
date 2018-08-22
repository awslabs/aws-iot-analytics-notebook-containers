import asyncio
import base64
import boto3
import docker
import json
import os
import time
import traceback

from iota_notebook_containers.constants import SAGEMAKER_FOLDER
from iota_notebook_containers.containerized_kernel_utils import remove_containerized_prefix
from iota_notebook_containers.containerization_status_log_entry import ContainerizationStatusLogEntry
from iota_notebook_containers.containerization_status_logger_builder import ContainerizationStatusLoggerBuilder
from iota_notebook_containers.export_to_ecr_params_validator import ImageCreationAndUploadParamsValidator
from iota_notebook_containers.kernel_image_creator import KernelImageCreator

from collections import namedtuple
from http import HTTPStatus

import logging
from threading import Lock
from tornado import websocket
from tornado.ioloop import IOLoop
from tornado.platform.asyncio import AnyThreadEventLoopPolicy
from tornado.web import RequestHandler

ECR = "ecr"
INTERIM_TAG = "interim"
LATEST_TAG = "latest"

CONTAINER_NAME = "@iota_container_name"
CONTAINER_DESCRIPTION = "@iota_container_description"
SCHEMA_VERSION = "@schema_version"
ONGOING_CONTAINERIZATION_ERROR_MSG = "We only support one containerization process at a time per instance."
ONGOING_CONTAINERIZATION_LOG_MSG = "Blocking a containerization attempt as a containerization process is already ongoing."
CONTAINERIZATION_UNHANDLED_ERROR_MSG = "A problem occurred during the containerization process. " + \
    "Please try again. If the problem persists, contact AWS Iot Analytics Technical Support."
ImageUploadStatus = namedtuple("ImageUploadStatus", "progress error_msg error_trace")
logger = logging.getLogger(__name__)


class CreateNewRepoHandler(RequestHandler):
    def post(self):
        repository_name = self.get_body_argument("repository_name")
        self.write(self.create_new_repo(repository_name))

    @classmethod
    def create_new_repo(cls, repository_name):
        ecr_client = boto3.client(ECR)
        ecr_client.create_repository(repositoryName=repository_name)
        return json.dumps({"repositoryName": repository_name})


class ListRepoHandler(RequestHandler):
    def get(self):
        next_token = self.get_body_argument("next_token", None)
        self.write(self.list_repos(next_token))

    @classmethod
    def list_repos(cls, input_next_token=None):
        ecr_client = boto3.client(ECR)
        if input_next_token:
            describe_repositories_response = ecr_client.describe_repositories(nextToken=input_next_token)
        else:
            describe_repositories_response = ecr_client.describe_repositories()
        output_repositories = [repository["repositoryName"]
            for repository in describe_repositories_response["repositories"]]
        output_next_token = describe_repositories_response.get("nextToken", None)
        return json.dumps(
            {"repositories": output_repositories, "next_token": output_next_token})


class IsContainerizationOngoingHandler(RequestHandler):
    def get(self):
        is_ongoing = self.is_containerization_ongoing()
        self.write(json.dumps(is_ongoing))

    @classmethod
    def is_containerization_ongoing(cls):
        return UploadToRepoHandler.containerization_lock.locked()


class UploadToRepoHandler(websocket.WebSocketHandler):
    containerization_lock = Lock()
    containerizing_client = None
    LAYER_EXISTS_MSG = "Layer already exists"
    # this status update does not contain novel information so we skip it
    REFERS_TO_REPO_PREFIX = "The push refers to repository"

    def open(self):
        if UploadToRepoHandler.containerization_lock.acquire(blocking=False):
            UploadToRepoHandler.containerizing_client = self
        else:
            logger.info(ONGOING_CONTAINERIZATION_LOG_MSG)
            raise RuntimeError(ONGOING_CONTAINERIZATION_ERROR_MSG)

    def on_close(self):
        if UploadToRepoHandler.containerizing_client is self:
            UploadToRepoHandler.containerizing_client = None
            UploadToRepoHandler.containerization_lock.release()

    async def on_message(self, message):
        asyncio.set_event_loop_policy(AnyThreadEventLoopPolicy())
        parsed_message = json.loads(message)

        invalid_params_resp = await self.get_invalid_params_resp(parsed_message)
        if invalid_params_resp:
            self.write_message(invalid_params_resp.as_dict())
            self.close()

        notebook_path = os.path.join(SAGEMAKER_FOLDER, parsed_message["notebook_path"].lstrip("/"))

        containerization_status_logger = ContainerizationStatusLoggerBuilder.build(
            notebook_path)
        log_time_fields = {"containerization_start": time.time(),
            "notebook_modification_time": os.path.getmtime(notebook_path)}

        initial_status = ContainerizationStatusLogEntry.of_image_creation(
            notebook_path, error_msg=None, progress=0)
        self.log_and_write_status(containerization_status_logger, initial_status)

        last_status = initial_status
        try:
            containerized_kernel_name = parsed_message["kernel_name"]
            annotations = self.get_manifest_annotations(
                parsed_message["variables"],
                parsed_message["container_name"],
                parsed_message["container_description"])
            repository_name = parsed_message["repository_name"]
            repository_uri = await self.get_repository_uri(repository_name)

            if not repository_uri:
                error_msg = "Destination repository {} does not exist.".format(
                    repository_name)
                log_entry = ContainerizationStatusLogEntry.of_image_creation(
                    notebook_path, error_msg=error_msg, progress=0)
                self.log_and_write_status(containerization_status_logger, log_entry)
                self.clear()
                self.close(HTTPStatus.NOT_FOUND)
                return

            statuses = self.containerize_and_upload(repository_name, repository_uri,
                containerized_kernel_name, notebook_path, log_time_fields, annotations)
            async for status in statuses:
                last_status = status
                self.log_and_write_status(containerization_status_logger, status)
                if status.error_msg:
                    self.close(HTTPStatus.OK)
                    return
        except:
            last_status.error_msg = CONTAINERIZATION_UNHANDLED_ERROR_MSG
            last_status.error_trace = traceback.format_exc()
            self.log_and_write_status(containerization_status_logger, last_status)
            logger.exception()
            raise
        finally:
            self.close(HTTPStatus.OK)

    @classmethod
    async def get_invalid_params_resp(cls, params):
        error_msg = await ImageCreationAndUploadParamsValidator.get_invalid_params_msg(params)
        if error_msg:
            return ContainerizationStatusLogEntry.of_image_creation(
                params.get("notebook_path", None), error_msg=error_msg, progress=0)

    @classmethod
    def get_manifest_annotations(cls, variables, container_name, container_description):
        output = {
            SCHEMA_VERSION: "1.0.0",
            CONTAINER_NAME: container_name,
            CONTAINER_DESCRIPTION: container_description
        }

        for variable in variables:
            type_desc_dict = {
                "type": variable["type"],
                "description": variable["description"] if variable["description"] else None
            }
            output[variable["name"]] = json.dumps(type_desc_dict)
        return output

    def log_and_write_status(self, containerization_status_logger, log_entry):
        containerization_status_logger.info(log_entry)
        self.write_message(log_entry.as_dict())

    @classmethod
    async def containerize_and_upload(cls, repository_name, repository_uri, containerized_kernel_name, notebook_path, log_time_fields, annotations):
        creation_status_gen = cls.run_image_creation(containerized_kernel_name, notebook_path, log_time_fields)
        async for image_creation_status, image in cls.iterate_in_executor(creation_status_gen):
            yield image_creation_status
        upload_status_gen = cls.run_image_upload(repository_name, repository_uri, image, notebook_path, log_time_fields, annotations)
        async for image_upload_status in cls.iterate_in_executor(upload_status_gen):
            yield image_upload_status

    @classmethod
    async def iterate_in_executor(cls, gen):
        while True:
            next_item = await IOLoop.current().run_in_executor(None, next, gen, None)
            if not next_item:
                break
            yield next_item

    @classmethod
    def run_image_creation(cls, containerized_kernel_name, notebook_path, log_time_fields):
        for uncapped_image_creation_status in KernelImageCreator.create(containerized_kernel_name, notebook_path):
            image_creation_status = cls.cap_if_not_final_status(
                uncapped_image_creation_status)
            status_to_log = cls.add_time_fields_and_remove_image(image_creation_status,
                log_time_fields)
            yield ContainerizationStatusLogEntry.of_image_creation(
                notebook_path, **status_to_log), image_creation_status.image

    @classmethod
    def add_time_fields_and_remove_image(cls, status, log_time_fields):
        status_dict = status._asdict()
        if "image" in status_dict:
            del status_dict["image"]
        return {**status_dict, **log_time_fields}

    @classmethod
    def cap_if_not_final_status(cls, uncapped_image_creation_status):
        # if an image was returned, the process is complete and we do not need to cap the progress
        if uncapped_image_creation_status.image:
            return uncapped_image_creation_status

        return UploadToRepoHandler.cap_progress(uncapped_image_creation_status)

    @classmethod
    def run_image_upload(cls, repository_name, repository_uri, image, notebook_path, log_time_fields, annotations):
        for image_upload_status in cls.upload_image_to_repo(
            repository_name, repository_uri, image, annotations):
                status_to_log = cls.add_time_fields_and_remove_image(
                    image_upload_status, log_time_fields)
                yield ContainerizationStatusLogEntry.of_image_upload(
                    notebook_path, **status_to_log)

    @classmethod
    async def get_repository_uri(cls, repository_name):
        ecr_client = boto3.client(ECR)
        try:
            matching_repositories = ecr_client.describe_repositories(repositoryNames=[repository_name])
            return matching_repositories["repositories"][0]["repositoryUri"]
        except: 
            return None

    @classmethod
    def upload_image_to_repo(cls, repository_name, repository_uri, image, annotations):
        ecr_client = boto3.client(ECR)
        token = ecr_client.get_authorization_token()["authorizationData"][0]["authorizationToken"]
        username, password = base64.b64decode(token).decode().split(":")
        auth_config = {"username": username, "password": password}
        docker_client = docker.from_env(timeout=600)
        docker_client.api.tag(image, repository=repository_uri + ":" + INTERIM_TAG)
        previous_progress = None
        for push_status_bytes in docker_client.api.push(repository=repository_uri + ":" + INTERIM_TAG, stream=True, auth_config=auth_config):
            parsed_status = cls.parse_upload_status(push_status_bytes.decode())
            if parsed_status and cls.status_should_be_reported(parsed_status, previous_progress):
                previous_progress = parsed_status.progress
                yield UploadToRepoHandler.cap_progress(parsed_status)
                if parsed_status.error_msg:
                    return

        cls.add_annotations_to_manifest(repository_name, annotations)
        yield ImageUploadStatus(progress=100, error_msg=None, error_trace=None)

    @classmethod
    def status_should_be_reported(cls, status, previous_progress):
        return bool(status.error_msg or status.progress != previous_progress)

    @classmethod
    def add_annotations_to_manifest(cls, repository_name, annotations):
        ecr_client = boto3.client(ECR)
        manifest = json.loads(ecr_client.batch_get_image(repositoryName=repository_name,
            imageIds=[{'imageTag':INTERIM_TAG}])["images"][0]["imageManifest"])
        manifest["annotations"] = annotations
        ecr_client.put_image(repositoryName=repository_name,
            imageManifest=json.dumps(manifest), imageTag=LATEST_TAG)
        ecr_client.batch_delete_image(repositoryName=repository_name,
            imageIds=[{'imageTag':INTERIM_TAG}])
      
    @classmethod
    def parse_upload_status(cls, push_info):
        try:
            push_info = json.loads(push_info)
        except json.decoder.JSONDecodeError:
            return None

        if "status" not in push_info or cls.REFERS_TO_REPO_PREFIX in push_info["status"]:
            return None

        # sometimes progressDetail is not present, sometimes it's empty
        if not push_info.get("progressDetail", None):
            return None

        progress_detail = push_info["progressDetail"]
        if progress_detail == cls.LAYER_EXISTS_MSG:
            return ImageUploadStatus(progress=100, error_trace=None,
                error_msg="This image has already been uploaded to this repository.")

        data_pushed_so_far = progress_detail["current"]
        total_data = progress_detail["total"]
        progress = int(100 * float(data_pushed_so_far)/total_data)

        return ImageUploadStatus(progress=progress, error_msg=None, error_trace=None)

    @classmethod
    def cap_progress(cls, status):
        # we don't want to report completion until everything is entirely finished
        if status.progress and status.progress > 99:
            return status._replace(progress=99)
        else:
            return status

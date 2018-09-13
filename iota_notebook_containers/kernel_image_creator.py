"""
Create image from containerized kernel
Steps:
    1. Copy the containerized kernel
    2. Copy all env variables and files along the sys paths of the kernel's python env onto that copy
    3. Commit the container to OUTPUT_IMAGE
    4. Set the entrypoint to a script that will run the notebook with the appropriate python executable
"""
import ast
import docker
import logging
import os
import shutil
import subprocess
import tarfile
import traceback

from collections import namedtuple
from hurry.filesize import size
from io import BytesIO
from pathlib import Path

from iota_notebook_containers.constants import CONTAINER_NAME, SAGEMAKER_FOLDER, AWS_SETTINGS_FOLDER
from iota_notebook_containers.containerized_kernel_utils import remove_containerized_prefix
from environment_kernels import EnvironmentKernelSpecManager

ImageCreationStatus = namedtuple("ImageCreationStatus", "progress image error_msg error_trace")

class KernelImageCreator(object):
    ASTTOKENS_PACKAGE = "asttokens==1.1.10"
    CONDA_PREFIX = "conda_"
    DOCKER_TIMEOUT = 600
    ENV_FOLDER = "/home/ec2-user/anaconda3/envs/"
    EXCLUDE_FROM_CP = ".pyc"
    FAILURE_MSG = "Image creation failed."
    INTERIM_CONTAINER_NAME = "interim_containerized_kernel"
    MAX_FILEBATCH_SIZE = 512 * 1024 * 1024 # 0.5 gb
    NOTEBOOK_EXECUTION_FILE = "iota_run_nb.py"
    NOTEBOOK_EXECUTION_FILEPATH = "/home/ec2-user/iota_run_nb.py"
    NOTEBOOK_PATH_ENV_VAR = "NOTEBOOK_PATH"
    OUTPUT_IMAGE = "output_image"
    SPACE_REQUIREMENT_FUDGE_BYTES = 10 * 1024 * 1024 # 10 mb
    # we multiply by 1.9 because the data will be duplicated while it is stored in
    # both the container and the image. this is a conservative estimate because the
    # image is compressed. a quick empirical measure found the space use to be
    # 1.45 times the disk space.
    # 2x would be safer, but that would block instances with the current amount
    # of free space from containerizing images
    REQUIRED_SPACE_PER_FILES_SPACE = 1.9

    logger = logging.getLogger(__name__)
    docker_client = docker.from_env(timeout=DOCKER_TIMEOUT)

    @classmethod
    def create(cls, containerized_kernel, notebook_path):
        try:
            cls.logger.info("Clearing any pre-existing output images or containers")
            cls._delete_output_container_and_image()
            kernel = remove_containerized_prefix(containerized_kernel)
            cls._copy_notebook_execution_file_to_dest()
            python_executable = cls._get_env_python_executable(kernel)

            cls.logger.info("Installing asttokens.")
            pip_path = os.path.join(os.path.dirname(python_executable), "pip")
            # this package is required by iota_run_nb.py
            subprocess.check_output([pip_path, "install", "-q", cls.ASTTOKENS_PACKAGE])

            folders_to_copy = cls._get_folders_to_copy(kernel, python_executable)
            insufficient_space_msg = cls._get_message_if_space_insufficient(
                cls._generate_files_to_copy(folders_to_copy, cls.EXCLUDE_FROM_CP))
            if insufficient_space_msg:
                yield ImageCreationStatus(progress=0, image=None,
                    error_msg=insufficient_space_msg, error_trace=None)
                return

            original_container = cls.docker_client.containers.get(CONTAINER_NAME)
            interim_container = cls._create_interim_container(original_container, containerized_kernel, notebook_path)
            interim_container.start()

            cls.logger.info("Copying files onto the container.")
            total_to_copy = cls._get_total_size_of_files(cls._generate_files_to_copy(folders_to_copy, cls.EXCLUDE_FROM_CP))
            total_copied = 0
            for filepaths in cls._split_into_batches(cls._generate_files_to_copy(folders_to_copy, cls.EXCLUDE_FROM_CP)):
                cls._copy_onto_container(interim_container, filepaths)
                total_copied += cls._get_total_size_of_files(filepaths)
                progress = int(100*float(total_copied)/total_to_copy)
                yield ImageCreationStatus(progress=progress, image=None, error_msg=None, error_trace=None)

            cls.logger.info("Writing the container to an image.")
            interim_container.commit(cls.OUTPUT_IMAGE,
                changes='ENTRYPOINT ["{}","{}"]'.format(python_executable, cls.NOTEBOOK_EXECUTION_FILEPATH))
            cls.logger.info("Containerization complete.")
            image = cls.docker_client.images.get(cls.OUTPUT_IMAGE).id
            yield ImageCreationStatus(progress=100, image=image, error_msg=None, error_trace=None)
        except Exception as exception:
            cls.logger.exception("Caught unhandled exception while creating the image.")
            yield ImageCreationStatus(progress=0, image=None, error_msg=cls.FAILURE_MSG,
                error_trace=traceback.format_exc())
            raise
        finally:
            cls._delete_interim_container()

    @classmethod
    def _copy_notebook_execution_file_to_dest(cls):
        # move the notebook execution file to the intended location on the final image
        # creating a copy allows us to re-use the other logic that assumes we want the dest filepath
        # to match the source filepath
        src = os.path.join(os.path.dirname(__file__), cls.NOTEBOOK_EXECUTION_FILE)
        os.makedirs(os.path.dirname(cls.NOTEBOOK_EXECUTION_FILEPATH), exist_ok=True)
        shutil.copy(src, cls.NOTEBOOK_EXECUTION_FILEPATH)

    @classmethod
    def _get_folders_to_copy(cls, kernel, python_executable):
        command = [python_executable, "-c", "import sys; print(sys.path)"]
        sys_paths = ast.literal_eval(str(subprocess.check_output(command), "utf-8"))
        kernel_without_prefix = cls._remove_prefix(kernel, cls.CONDA_PREFIX)

        return sys_paths + [os.path.dirname(python_executable)] + [SAGEMAKER_FOLDER, AWS_SETTINGS_FOLDER] + [
            os.path.join(cls.ENV_FOLDER, kernel_without_prefix)]

    @classmethod
    def _remove_prefix(cls, text, prefix):
        if text.startswith(prefix):
            return text[len(prefix):]
        return text

    @classmethod
    def _get_env_python_executable(cls, kernel):
        return EnvironmentKernelSpecManager().get_kernel_spec(kernel).argv[0]

    @classmethod
    def _get_total_size_of_files(cls, filepaths):
        total_bytes = 0
        for filepath in filepaths:
            total_bytes += os.path.getsize(filepath)
        return total_bytes

    @classmethod
    def _get_message_if_space_insufficient(cls, paths_to_copy):
        INSUFFIENT_SPACE_ERROR_FMT = "There is insufficient space remaining on this instance to " + \
        "containerize this notebook. Containerization would require {} of additional space."

        files_to_copy_bytes = cls._get_total_size_of_files(paths_to_copy)
        _, _, free_space_bytes = shutil.disk_usage("/")

        required_bytes = int(cls.REQUIRED_SPACE_PER_FILES_SPACE * files_to_copy_bytes
            ) + cls.SPACE_REQUIREMENT_FUDGE_BYTES

        if required_bytes > free_space_bytes:
            cls.logger.info("Insufficient space to containerize. Has {} bytes, requires {} bytes, " +
                "with fudge space requires {} bytes.".format(
                    free_space_bytes, files_to_copy_bytes, required_bytes))

            additional_required_bytes = required_bytes - free_space_bytes
            human_readable_additional_space_required = size(required_bytes - free_space_bytes)
            return INSUFFIENT_SPACE_ERROR_FMT.format("{} bytes ({})".format(
                additional_required_bytes, human_readable_additional_space_required))
            
    @classmethod
    def _create_interim_container(cls, original_container, kernel, notebook_path):
        cls._delete_interim_container()

        environment = EnvironmentKernelSpecManager().get_kernel_spec(kernel).env
        environment[cls.NOTEBOOK_PATH_ENV_VAR] = notebook_path

        interim_container_creation_result = cls.docker_client.api.create_container(
            name=cls.INTERIM_CONTAINER_NAME,
            image=original_container.image.id,
            volumes=None,
            stdin_open=True,
            detach=True,
            host_config={"network_mode": "host"},
            environment=environment
        )

        if interim_container_creation_result["Warnings"]:
            cls.logger.warning("Warning encountered during interim container creation",
                interim_container_creation_result["Warnings"])
        return cls.docker_client.containers.get(interim_container_creation_result["Id"])

    @classmethod
    def _delete_interim_container(cls):
        if cls.INTERIM_CONTAINER_NAME in (container.name for container in cls.docker_client.containers.list(all=True)):
            interim_container = cls.docker_client.containers.get(cls.INTERIM_CONTAINER_NAME)
            interim_container.stop()
            interim_container.remove()

    @classmethod
    def _generate_files_to_copy(cls, sys_paths, *exclude_exts):
        yield cls.NOTEBOOK_EXECUTION_FILEPATH
        candidate_paths = set(sys_paths)
        paths_to_copy = set([path for path in candidate_paths - cls._get_child_paths(candidate_paths)
            if os.path.exists(path)])

        for path in sorted(paths_to_copy):
            for root, subdirs, files in os.walk(path, followlinks=True):
                for f in sorted(files):
                    _, ext = os.path.splitext(f)
                    if not exclude_exts or ext not in exclude_exts:
                        filepath = os.path.join(root, f)
                        yield filepath

    @classmethod
    def _get_child_paths(cls, paths):
        child_paths = set()
        for path1 in paths:
            for path2 in paths:
                if Path(path2) in Path(path1).parents:
                    child_paths.add(path1)
        return child_paths

    @classmethod
    def _split_into_batches(cls, filepaths):
        total_size = 0
        filepath_batch = []

        for filepath in filepaths:
            file_size = os.path.getsize(filepath)
            if file_size + total_size <= cls.MAX_FILEBATCH_SIZE:
                filepath_batch.append(filepath)
                total_size += file_size
            else:
                yield filepath_batch
                filepath_batch = [filepath]
                total_size = file_size
        if filepath_batch:
            yield filepath_batch

    @classmethod
    def _copy_onto_container(cls, interim_container, filepaths):
        tarstream = BytesIO()
        with tarfile.TarFile(fileobj=tarstream, mode="w") as tar:
            for filepath in filepaths:
                tar.add(filepath)
        tarstream.seek(0)
        interim_container.put_archive("/", tarstream)

    @classmethod
    def _delete_output_container_and_image(cls):
        try:
            output_image = cls.docker_client.images.get(cls.OUTPUT_IMAGE)
            for container in cls.docker_client.containers.list(all=True):
                if container.image == output_image:
                    container.stop()
                    container.remove()
            cls.docker_client.images.remove(output_image.id, force=True)
        except docker.errors.ImageNotFound:
            pass

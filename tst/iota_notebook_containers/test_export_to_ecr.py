import asyncio
import boto3
import docker
import json
import urllib
import tornado

import moto
import unittest

from datetime import datetime
from http import HTTPStatus
import time

from freezegun import freeze_time
from tornado.testing import AsyncHTTPTestCase
from unittest.mock import patch, MagicMock

from iota_notebook_containers.containerization_status_log_entry import ContainerizationStatusLogEntry
from iota_notebook_containers.kernel_image_creator import KernelImageCreator, ImageCreationStatus
from iota_notebook_containers.export_to_ecr import CreateNewRepoHandler, ListRepoHandler, \
    UploadToRepoHandler, IsContainerizationOngoingHandler, ImageUploadStatus, ECR, LATEST_TAG, \
    INTERIM_TAG

@moto.mock_ecr
class TestCreateNewRepoHandler(AsyncHTTPTestCase):
    REPO_NAME = "test_repo"
    DATE_STR = "2012-01-14"

    def setUp(self):
        super().setUp()
        self.ecr_client = boto3.client(ECR)
        self.container_name = "aName"
        self.container_description = "a description"
        self.expected_annotations = {
            "@schema_version": "1.0.0",
            "@iota_container_name": self.container_name,
            "@iota_container_description": self.container_description
        }
        self.input_params = {
            "container_name": "name",
            "container_description": "desc",
            "notebook_path": "some_path",
            "kernel_name": "containerized_conda_python3",
            "variables": [{"name": "valid_name", "type": "string", "description": ""}],
            "repository_name": self.REPO_NAME
        }

        if UploadToRepoHandler.containerization_lock.locked():
            UploadToRepoHandler.containerization_lock.release()

    @classmethod
    def setUpClass(cls):
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)

    def get_app(self):
        application = tornado.web.Application([
            (r"/create_repo", CreateNewRepoHandler),
            (r"/upload_to_repo", UploadToRepoHandler),
            (r"/list_repos", ListRepoHandler),
            (r"/upload_to_repo/is_ongoing", IsContainerizationOngoingHandler),
        ])
        return application

    def list_all_repos(self):
        repositories = []
        next_token = None
        while True:
            response = json.loads(ListRepoHandler.list_repos(next_token))
            repositories.extend(response["repositories"])
            next_token = response["next_token"]
            if not next_token:
                break
        return repositories

    def delete_all_repos(self):
        repositories = self.list_all_repos()
        ecr_client = boto3.client(ECR)
        for repo in repositories:
            ecr_client.delete_repository(repositoryName=repo)

    def tearDown(self):
        self.delete_all_repos()

    @tornado.testing.gen_test
    def test_list_repos_no_repos(self):
        # WHEN
        response = yield self.http_client.fetch(self.get_url("/list_repos"))

        # THEN
        self.assertEquals(HTTPStatus.OK, response.code)
        response_data = json.loads(response.body)
        self.assertEquals([], response_data["repositories"])
        self.assertEquals(None, response_data["next_token"])
        self.assertEquals([], self.list_all_repos())

    @tornado.testing.gen_test
    def test_create_new_repo(self):
        # WHEN
        body = urllib.parse.urlencode({"repository_name": self.REPO_NAME})
        response = yield self.http_client.fetch(self.get_url("/create_repo"), method="POST", body=body)

        # THEN
        self.assertEquals(HTTPStatus.OK, response.code)
        expected_response_body = {"repositoryName": self.REPO_NAME}
        observed_response_body = json.loads(response.body)
        self.assertDictEqual(expected_response_body, observed_response_body)
        repositories = self.list_all_repos()
        self.assertEquals([self.REPO_NAME], repositories)

    @tornado.testing.gen_test
    def test_list_repos_3_repos(self):
        # GIVEN
        repo_names = ["repo1", "repo2", "repo3"]
        for repo_name in repo_names:
            CreateNewRepoHandler.create_new_repo(repo_name)

        # WHEN
        response = yield self.http_client.fetch(self.get_url("/list_repos"))

        # THEN
        self.assertEquals(HTTPStatus.OK, response.code)
        response_data = json.loads(response.body)
        self.assertCountEqual(repo_names, response_data["repositories"])
        self.assertEquals(response_data["next_token"], None)

    @tornado.testing.gen_test(timeout=10)
    def test_list_repos_1000_repos(self):
     # GIVEN
     NUM_REPOS = 1000
     repo_names = ["repo" + str(i) for i in range(NUM_REPOS)]

     # WHEN
     for repo_name in repo_names:
         CreateNewRepoHandler.create_new_repo(repo_name)
     
    # THEN
     observed_repos = []
     next_token = None
     while True:
        response = yield self.http_client.fetch(self.get_url("/list_repos"))
        self.assertEquals(HTTPStatus.OK, response.code)
        response_data = json.loads(response.body)
        observed_repos.extend(response_data["repositories"])
        next_token = response_data["next_token"]
        if not next_token:
            break

        self.assertCountEqual(repo_names, observed_repos)

    def test_get_repository_uri(self):
        # GIVEN 
        async def get_async_result():
            return await UploadToRepoHandler.get_repository_uri(self.REPO_NAME)
        current = asyncio.get_event_loop().run_until_complete(get_async_result())
        self.assertEquals(None, current)

        # WHEN
        CreateNewRepoHandler.create_new_repo(self.REPO_NAME)

        # THEN 
        ecr_client = boto3.client(ECR)
        expected = ecr_client.describe_repositories(repositoryNames=[self.REPO_NAME])["repositories"][0]["repositoryUri"]
        actual = asyncio.get_event_loop().run_until_complete(get_async_result())
        self.assertEquals(expected, actual)

    @tornado.testing.gen_test
    def test_upload_image_to_repo(self):
        # GIVEN
        IMAGE = "image"
        OUTPUT = json.dumps({"status": "someStatus"})
        ecr_client = boto3.client(ECR)
        repository_uri = ecr_client.create_repository(repositoryName=self.REPO_NAME)["repository"]["repositoryUri"]
        variables = [
            {"name": "var1", "type": "string", "description": ""},
            {"name": "var2", "type": "double", "description": "best var"}
        ]
        expected_annotations = {**self.expected_annotations, 
            "var1": json.dumps({"type": "string", "description": None}),
            "var2": json.dumps({"type": "double", "description": "best var"})
        }

        KernelImageCreator.create = lambda x, y: [ImageCreationStatus(progress=100, image=IMAGE, error_msg=None, error_trace=None)]
        notebook_modification_time = time.time()

        ecr_client = boto3.client("ecr")
        ecr_client.batch_get_image = lambda **kwargs: {"images": [{"imageManifest": "{}"}]}
        put_image_mock = MagicMock()
        ecr_client.put_image = put_image_mock
        batch_delete_image_mock = MagicMock()
        ecr_client.batch_delete_image = batch_delete_image_mock

        mock_logger = MagicMock()
        mock_logger_info = MagicMock()
        mock_logger.info = mock_logger_info
        docker_client = MagicMock()
        docker_client.api.push.return_value = [str.encode(OUTPUT)]

        # WHEN
        with freeze_time(datetime.fromtimestamp(int(time.time()))):
            frozen_time = time.time()
            with patch("docker.from_env", return_value=docker_client):
                with patch("os.path.getmtime", return_value=notebook_modification_time):
                    with patch("logging.getLogger", return_value=mock_logger):
                        with patch("logging.handlers.RotatingFileHandler.__init__", return_value=None):
                            with patch("boto3.client", return_value=ecr_client):
                                payload = {"repository_name": self.REPO_NAME, "variables": variables, 
                                    "container_name": self.container_name,
                                    "container_description": self.container_description,
                                    "kernel_name": "containerized_conda_python3",
                                    "notebook_path": "irrelevant"
                                }
                                request_url = "ws://localhost:" + str(self.get_http_port()) + "/upload_to_repo"
                                ws = yield tornado.websocket.websocket_connect(request_url)
                                ws.write_message(json.dumps(payload))
                                observed_output = []
                                while True:
                                    response = yield ws.read_message()
                                    if not response:
                                        break
                                    observed_output.append(response)

        # THEN
        self.assertEquals(HTTPStatus.OK, ws.close_code)
        docker_client.api.tag.assert_called_once_with(IMAGE, repository=repository_uri + ":" + INTERIM_TAG)
        auth_config = {"username": "AWS", "password": "us-east-1-auth-token"}
        docker_client.api.push.assert_called_once_with(auth_config=auth_config, repository=repository_uri + ":" + INTERIM_TAG, stream=True)

        self.assertEquals(3, len(observed_output))
        self.assertEquals("image_creation", json.loads(observed_output[0])["step"])
        self.assertEquals("image_creation", json.loads(observed_output[1])["step"])
        self.assertEquals("image_upload", json.loads(observed_output[2])["step"])

        self.assertEquals(0, json.loads(observed_output[0])["progress"])
        for response_json in observed_output[1:]:
            response_data = json.loads(response_json)
            self.assertEquals(100, response_data["progress"])
            self.assertEquals(None, response_data["error_msg"])
            self.assertEquals(None, response_data["error_trace"])

        self.assertEquals(3, len(mock_logger_info.call_args_list))
        self.assertEquals("image_creation", mock_logger_info.call_args_list[0][0][0].step)
        self.assertEquals("image_creation", mock_logger_info.call_args_list[1][0][0].step)
        self.assertEquals("image_upload", mock_logger_info.call_args_list[2][0][0].step)

        for logged_info in mock_logger_info.call_args_list[1:]:
            log_entry = logged_info[0][0]
            self.assertEquals(frozen_time, log_entry.epoch_timestamp)
            self.assertEquals(frozen_time, log_entry.containerization_start)
            self.assertEquals(notebook_modification_time, log_entry.notebook_modification_time)
            self.assertEquals(100, log_entry.progress)
            self.assertEquals(None, log_entry.error_msg)
            self.assertEquals(None, log_entry.error_trace)
            self.assertEquals("1.0.0", log_entry.version)
            self.assertEquals("irrelevant", log_entry.notebook_path)

        put_image_mock.assert_called_once_with(imageManifest=json.dumps({'annotations': expected_annotations}),
            imageTag=LATEST_TAG, repositoryName=self.REPO_NAME)
        batch_delete_image_mock.assert_called_once_with(imageIds=[{'imageTag': INTERIM_TAG}], repositoryName=self.REPO_NAME)

    @tornado.testing.gen_test
    def test_upload_image_to_nonexisting_repo(self):
        # GIVEN
        IMAGE = "image"
        OUTPUT = "output"
        ecr_client = boto3.client(ECR)
        KernelImageCreator.create = lambda x, y: [ImageCreationStatus(progress=100, image=IMAGE, error_msg=None, error_trace=None)]
        mock_logger = MagicMock()

        # WHEN
        payload = {"repository_name": self.REPO_NAME,
            "kernel_name": "containerized_conda_python3", "notebook_path": "irrelevant",
            "container_name": "name", "container_description": "desc", "variables": []}
        request_url = "ws://localhost:" + str(self.get_http_port()) + "/upload_to_repo"
        with patch("os.path.getmtime", return_value=time.time()):
            with patch("logging.getLogger", return_value=mock_logger):
                with patch("logging.handlers.RotatingFileHandler.__init__", return_value=None):
                    ws = yield tornado.websocket.websocket_connect(request_url)
                    ws.write_message(json.dumps(payload))
                    while True:
                        response = yield ws.read_message()
                        if not response:
                            break

        # THEN
        self.assertEqual(HTTPStatus.NOT_FOUND, ws.close_code)

    @tornado.testing.gen_test
    @patch('iota_notebook_containers.export_to_ecr.UploadToRepoHandler.add_annotations_to_manifest')
    @patch("docker.from_env", MagicMock())
    def test_GIVEN_redundant_progress_WHEN_upload_image_to_repo_THEN_filter(self, add_annotations_to_manifest):
        # GIVEN
        repository_uri = self.ecr_client.create_repository(
            repositoryName=self.REPO_NAME)["repository"]["repositoryUri"]
        status_dict = {"status": "pushing", "progressDetail": {"total": 100, "current": 10}}
        statuses = (str.encode(json.dumps(status_dict)), str.encode(json.dumps(status_dict)))
        docker_client = docker.from_env()
        docker_client.api.push.return_value = statuses
        add_annotations_to_manifest = MagicMock()

        # WHEN
        output_gen = UploadToRepoHandler.upload_image_to_repo(self.REPO_NAME, repository_uri, "", "")
        output_statuses = [status for status in output_gen]

        # THEN
        # verify only 2 are returned (instead of three)
        # there's an extra 100 progress status for marking completion
        expected = [ImageUploadStatus(progress=10, error_msg=None, error_trace=None),
            ImageUploadStatus(progress=100, error_msg=None, error_trace=None)]

        self.assertEquals(expected, output_statuses)

    @tornado.testing.gen_test
    @patch('iota_notebook_containers.export_to_ecr.UploadToRepoHandler.add_annotations_to_manifest')
    @patch("docker.from_env", MagicMock())
    def test_GIVEN_redundant_progress_with_error_WHEN_upload_image_to_repo_THEN_dont_filter(self, add_annotations_to_manifest):
        # GIVEN
        repository_uri = self.ecr_client.create_repository(
            repositoryName=self.REPO_NAME)["repository"]["repositoryUri"]      
        image = "image"
        status_dict1 = {"status": "pushing", "progressDetail": {"total": 100, "current": 99}}
        status_dict2 = {"status": "pushing", "progressDetail": UploadToRepoHandler.LAYER_EXISTS_MSG}
        statuses = (str.encode(json.dumps(status_dict1)), str.encode(json.dumps(status_dict2)))
        docker_client = docker.from_env()
        docker_client.api.push.return_value = statuses
        add_annotations_to_manifest = MagicMock()

        # WHEN
        output_gen = UploadToRepoHandler.upload_image_to_repo(self.REPO_NAME, repository_uri, image, "")
        output_statuses = [status for status in output_gen]

        # THEN
        error_msg = "This image has already been uploaded to this repository."
        expected = [ImageUploadStatus(progress=99, error_msg=None, error_trace=None),
            ImageUploadStatus(progress=99, error_msg=error_msg, error_trace=None)]
        self.assertEquals(expected, output_statuses)

    @tornado.testing.gen_test
    def test_GIVEN_diff_from_previous_progress_WHEN_status_should_be_reported_THEN_true(self):
        # GIVEN
        previous_progress = 1
        recent_progress = 2
        status = ImageUploadStatus(progress=recent_progress, error_msg=None, error_trace=None)

        # WHEN 
        observed = UploadToRepoHandler.status_should_be_reported(status, previous_progress)

        # THEN
        self.assertTrue(observed)

    @tornado.testing.gen_test
    def test_GIVEN_diff_from_previous_none_progress_WHEN_status_should_be_reported_THEN_true(self):
        # GIVEN
        previous_progress = None
        recent_progress = 2
        status = ImageUploadStatus(progress=recent_progress, error_msg=None, error_trace=None)

        # WHEN 
        observed = UploadToRepoHandler.status_should_be_reported(status, previous_progress)
        
        # THEN
        self.assertTrue(observed)

    @tornado.testing.gen_test
    def test_GIVEN_diff_from_previous_progress_WHEN_status_should_be_reported_THEN(self):
        # GIVEN
        previous_progress = 2
        recent_progress = 2
        status = ImageUploadStatus(progress=recent_progress, error_msg=None, error_trace=None)

        # WHEN 
        observed = UploadToRepoHandler.status_should_be_reported(status, previous_progress)
        
        # THEN
        self.assertFalse(observed)

    @tornado.testing.gen_test
    def test_GIVEN_diff_from_previous_progress_WHEN_status_should_be_reported_THEN(self):
        # GIVEN
        previous_progress = 2
        recent_progress = 2
        error_msg = "I exist!"
        status = ImageUploadStatus(progress=recent_progress, error_msg=error_msg, error_trace=None)

        # WHEN 
        observed = UploadToRepoHandler.status_should_be_reported(status, previous_progress)
        
        # THEN
        self.assertTrue(observed)

    @tornado.testing.gen_test
    def test_GIVEN_not_json_WHEN_parse_status_THEN_return_None(self):
        self.assertEquals(None, UploadToRepoHandler.parse_upload_status("test"))

    @tornado.testing.gen_test
    def test_GIVEN_no_status_WHEN_parse_status_THEN_return_None(self):
        status = json.dumps({"other": ""})
        self.assertEquals(None, UploadToRepoHandler.parse_upload_status(status))

    @tornado.testing.gen_test
    def test_GIVEN_this_push_refers_to_WHEN_parse_status_THEN_return_None(self):
        status = json.dumps({"status": UploadToRepoHandler.REFERS_TO_REPO_PREFIX})
        self.assertEquals(None, UploadToRepoHandler.parse_upload_status(status))

    @tornado.testing.gen_test
    def test_GIVEN_no_progress_detail_WHEN_parse_status_THEN_return_None(self):
        status = json.dumps({"status": {"key":"value"}})
        self.assertEquals(None, UploadToRepoHandler.parse_upload_status(status))

    @tornado.testing.gen_test
    def test_GIVEN_layer_already_upload_WHEN_parse_status_THEN_return_status_with_error(self):
        status = json.dumps({"status": "pushing", "progressDetail": UploadToRepoHandler.LAYER_EXISTS_MSG})
        expected = ImageUploadStatus(progress=100, error_trace=None, error_msg="This image has already been uploaded to this repository.")
        self.assertEquals(expected, UploadToRepoHandler.parse_upload_status(status))

    @tornado.testing.gen_test
    def test_GIVEN_current_and_total_WHEN_parse_status_THEN_return_status_with_progress(self):
        status = json.dumps({"status": "pushing", "progressDetail": {"total": 100, "current": 10}})
        expected = ImageUploadStatus(progress=10, error_msg=None, error_trace=None)
        self.assertEquals(expected, UploadToRepoHandler.parse_upload_status(status))

    @tornado.testing.gen_test
    def test_GIVEN_100_progress_WHEN_cap_progress_THEN_return_status_with_99_progress(self):
        # GIVEN
        uncapped = ImageUploadStatus(progress=100, error_msg=None, error_trace=None)
        expected = ImageUploadStatus(progress=99, error_msg=None, error_trace=None)
        
        # WHEN
        capped = UploadToRepoHandler.cap_progress(uncapped)

        # THEN
        self.assertEquals(expected, capped)

    @tornado.testing.gen_test
    def test_GIVEN_16_progress_WHEN_cap_progress_THEN_return_status_with_16_progress(self):
        # GIVEN
        uncapped = ImageUploadStatus(progress=16, error_msg=None, error_trace=None)
        
        # WHEN
        capped = UploadToRepoHandler.cap_progress(uncapped)

        # THEN
        self.assertEquals(uncapped, capped)

    @tornado.testing.gen_test
    def test_GIVEN_no_variables_WHEN_get_manifest_annotations_THEN_ONLY_NAME_AND_DESC(self):
        # GIVEN
        variables = []

        # WHEN 
        observed = UploadToRepoHandler.get_manifest_annotations(
            variables, self.container_name, self.container_description)

        # THEN
        self.assertCountEqual(self.expected_annotations, observed)

    @tornado.testing.gen_test
    def test_GIVEN_empty_desc_WHEN_get_manifest_annotations_THEN_null_desc(self):
        # GIVEN 
        variables = [{"type": "string", "description": "", "name": "name"}]

        # WHEN 
        observed = UploadToRepoHandler.get_manifest_annotations(
            variables, self.container_name, self.container_description)

        # THEN
        expected_annotations = {**self.expected_annotations, 
            "name": json.dumps(
                {"type": "string", "description": None})}
        self.assertCountEqual(expected_annotations, observed)

    @tornado.testing.gen_test
    def test_GIVEN_variables_WHEN_get_manifest_annotations_THEN_variables_in_manifest(self):
        # GIVEN
        variables = [{"type": "string", "description": "hi there!", "name": "name"}]

        # WHEN
        observed = UploadToRepoHandler.get_manifest_annotations(
            variables, self.container_name, self.container_description)

        # THEN
        expected_annotations = {**self.expected_annotations, 
        "name": json.dumps(
            {"type": "string", "description": "hi there!"})}
        self.assertCountEqual(expected_annotations, observed)

    @tornado.testing.gen_test
    def test_GIVEN_ongoing_containerization_WHEN_upload_to_repo_THEN_error_without_lock_clear(self):
        on_message_backup = UploadToRepoHandler.on_message
        def on_message(handler, message):
            handler.write_message("")
        try:
            UploadToRepoHandler.on_message = on_message
            self.assertFalse(IsContainerizationOngoingHandler.is_containerization_ongoing())
            request_url = "ws://localhost:" + str(self.get_http_port()) + "/upload_to_repo"
            # ws1 will acquire the lock and run successfully
            ws1 = yield tornado.websocket.websocket_connect(request_url)
            ws1.write_message(json.dumps(self.input_params))
            self.assertTrue(IsContainerizationOngoingHandler.is_containerization_ongoing())
            # ws2 should get blocked by ws1
            ws2 = yield tornado.websocket.websocket_connect(request_url)
            with self.assertRaises(tornado.websocket.WebSocketClosedError):
                ws2.write_message(json.dumps(self.input_params))
            self.assertTrue(IsContainerizationOngoingHandler.is_containerization_ongoing())
            # ws3 should also get blocked. we include it to verify that ws2's closure
            # does not clear ws1's lock
            ws3 = yield tornado.websocket.websocket_connect(request_url)
            with self.assertRaises(tornado.websocket.WebSocketClosedError):
                ws3.write_message(json.dumps(self.input_params))
            ws1.close()
            # with ws1 closed, ws4 should aquire the lock and run successfully
            ws4 = yield tornado.websocket.websocket_connect(request_url)
            ws4.write_message(json.dumps(self.input_params))
            response = yield ws4.read_message()
        finally:
            UploadToRepoHandler.on_message = on_message_backup

    @tornado.testing.gen_test
    def test_GIVEN_exception_raised_WHEN_upload_to_repo_THEN_socket_closed_and_lock_cleared(self):
        on_message_backup = UploadToRepoHandler.on_message
        def raise_error(*args):
            raise RuntimeError()
        try:
            UploadToRepoHandler.on_message = raise_error
            self.assertFalse(IsContainerizationOngoingHandler.is_containerization_ongoing())
            request_url = "ws://localhost:" + str(self.get_http_port()) + "/upload_to_repo"
            ws = yield tornado.websocket.websocket_connect(request_url)
            ws.write_message(json.dumps(self.input_params))
            response = yield ws.read_message()
            self.assertFalse(IsContainerizationOngoingHandler.is_containerization_ongoing())
            with self.assertRaises(tornado.websocket.WebSocketClosedError):
                ws.write_message(json.dumps(self.input_params))
        finally:
            UploadToRepoHandler.on_message = on_message_backup

    @tornado.testing.gen_test
    def test_GIVEN_websocket_closed_by_server_WHEN_upload_to_repo_THEN_lock_cleared(self):
        on_message_backup = UploadToRepoHandler.on_message
        def close_handler_if_arg_says_to(handler, should_close_handler):
            if json.loads(should_close_handler):
                handler.close()
            else:
                # write a message so that the test can wait upon the message elsewhere
                # as a means of ensuring that the on_open handler ran
                # otherwise, the logic would proceed asynchronously before the handler actually ran
                handler.write_message("")
        try:
            UploadToRepoHandler.on_message = close_handler_if_arg_says_to
            self.assertFalse(IsContainerizationOngoingHandler.is_containerization_ongoing())
            request_url = "ws://localhost:" + str(self.get_http_port()) + "/upload_to_repo"
            ws1 = yield tornado.websocket.websocket_connect(request_url)
            ws1.write_message(json.dumps(False))
            _ = yield ws1.read_message()
            self.assertTrue(IsContainerizationOngoingHandler.is_containerization_ongoing())
            old_containerizing_client = UploadToRepoHandler.containerizing_client
            self.assertNotEqual(None, old_containerizing_client)
            ws1.write_message(json.dumps(True))
            ws2 = yield tornado.websocket.websocket_connect(request_url)
            ws2.write_message(json.dumps(False))
            _ = yield ws2.read_message()
            # async logic makes it difficult to capture the moment there is no lock, but we can
            # verify that the new handler successfully attained the lock
            self.assertNotEqual(old_containerizing_client, UploadToRepoHandler.containerizing_client)
            self.assertNotEqual(None, UploadToRepoHandler.containerizing_client)
        finally:
            UploadToRepoHandler.on_message = on_message_backup

    @tornado.testing.gen_test
    def test_GIVEN_protocol_acting_as_ifclose_message_recieved_WHEN_upload_to_repo_THEN_lock_cleared(self):
        on_message_backup = UploadToRepoHandler.on_message
        def on_message(handler, message):
            handler.write_message("")
        try:
            UploadToRepoHandler.on_message = on_message
            self.assertFalse(IsContainerizationOngoingHandler.is_containerization_ongoing())
            request_url = "ws://localhost:" + str(self.get_http_port()) + "/upload_to_repo"
            ws1 = yield tornado.websocket.websocket_connect(request_url)
            ws1.write_message(json.dumps(False))
            _ = yield ws1.read_message()
            self.assertTrue(IsContainerizationOngoingHandler.is_containerization_ongoing())
            old_containerizing_client = UploadToRepoHandler.containerizing_client
            self.assertNotEqual(None, old_containerizing_client)
            # this is what the protocol object does when it recieves a close message request
            # i do this rather than send a close message request directly because it would be hard to
            # tell that i am not just introducing an exception, which we already know clears the lock
            # https://github.com/tornadoweb/tornado/blob/master/tornado/websocket.py#L1006
            ws1.protocol.close(ws1.protocol.handler.close_code)
            ws2 = yield tornado.websocket.websocket_connect(request_url)
            ws2.write_message(json.dumps(False))
            _ = yield ws2.read_message()
            self.assertNotEqual(old_containerizing_client, UploadToRepoHandler.containerizing_client)
            self.assertNotEqual(None, UploadToRepoHandler.containerizing_client)
        finally:
            UploadToRepoHandler.on_message = on_message_backup

    @tornado.testing.gen_test
    def test_GIVEN_not_ongoing_WHEN_is_containerization_ongoing_THEN_false(self):
        self.assertFalse(IsContainerizationOngoingHandler.is_containerization_ongoing())

    @tornado.testing.gen_test
    def test_GIVEN_is_ongoing_WHEN_is_containerization_ongoing_THEN_true(self):
        UploadToRepoHandler.containerization_lock.acquire(blocking=False)
        self.assertTrue(IsContainerizationOngoingHandler.is_containerization_ongoing())

    @tornado.testing.gen_test
    def test_GIVEN_not_ongoing_WHEN_fetch_is_containerization_ongoing_THEN_false(self):
        response = yield self.http_client.fetch(self.get_url("/upload_to_repo/is_ongoing"))
        self.assertFalse(json.loads(response.body))

    @tornado.testing.gen_test
    def test_GIVEN_is_ongoing_WHEN_fetch_is_containerization_ongoing_THEN_true(self):
        UploadToRepoHandler.containerization_lock.acquire(blocking=False)
        response = yield self.http_client.fetch(self.get_url("/upload_to_repo/is_ongoing"))
        self.assertTrue(json.loads(response.body))

    @freeze_time(DATE_STR)
    @tornado.testing.gen_test
    def test_GIVEN_invalid_var_name_WHEN_get_invalid_params_resp_THEN_fill_error_msg(self):
        # GIVEN
        self.input_params["variables"][0]["name"] = "@hi"

        # WHEN
        observed_msg = yield UploadToRepoHandler.get_invalid_params_resp(self.input_params)

        # THEN
        error_msg = "The following names are not valid python identifiers: @hi."
        expected_msg = ContainerizationStatusLogEntry.of_image_creation(self.input_params["notebook_path"], 
            error_msg=error_msg, progress=0)
        self.assertEqual(expected_msg, observed_msg)

    @freeze_time(DATE_STR)
    @tornado.testing.gen_test
    def test_GIVEN_valid_var_params_WHEN_get_invalid_params_resp_THEN_none(self):
        observed_resp = yield UploadToRepoHandler.get_invalid_params_resp(self.input_params)
        self.assertFalse(observed_resp)

    @freeze_time(DATE_STR)
    @tornado.testing.gen_test
    def test_GIVEN_no_notebook_path_WHEN_get_invalid_params_resp_THEN_still_return_error(self):
        # GIVEN
        del self.input_params["notebook_path"]

        # WHEN
        observed_resp = yield UploadToRepoHandler.get_invalid_params_resp(self.input_params)

        # THEN
        error_msg = "The following fields were not specified: notebook_path."
        expected_msg = ContainerizationStatusLogEntry.of_image_creation(None, error_msg=error_msg, progress=0)
        self.assertEqual(expected_msg, observed_resp)

if __name__ == '__main__':
    unittest.main()

"""
Tests the plugin UI
Usage: python selenium_test.py <chrome driver path>
Assumes a Chrome driver is present in the sys path
"""
import boto3
import os
import time
import sys
import threading

import moto
import unittest

from notebook.notebookapp import NotebookApp
from tornado.ioloop import IOLoop

from unittest.mock import patch, MagicMock
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from iota_notebook_containers.kernel_image_creator import KernelImageCreator


class TestPlugin(unittest.TestCase):
    def setUp(self):
        # create a temporary notebook file
        self.test_filename = "test.ipynb"
        self.test_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), self.test_filename)
        with open(self.test_file, "w") as f:
            f.write(
                """
              {"cells": [],
              "metadata": {
               "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
               },
               "language_info": {
                "codemirror_mode": {
                 "name": "ipython",
                 "version": 3
                },
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "pygments_lexer": "ipython3",
                "version": "3.6.4"
               }
              },
              "nbformat": 4,
              "nbformat_minor": 2
             }""")

    def tearDown(self):
        os.remove(self.test_file)
        self.app.stop()

    @moto.mock_ecr
    def test_run(self):
        CONTAINERIZE_OPTION = "containerize_option"
        CREATE_REPO_BUTTON = "#create_repo_button"
        IMAGE = "image"
        LATEST = ":latest"
        LISTED_REPOS = ".sorting_1"
        KERNEL_BUTTON = ".dropdown:nth-child(6) .dropdown-toggle"
        PROGRESS_BAR = "#progress_bar";
        REPO1 = "repo1"
        REPO2 = "repo2"
        REPO_CREATE_BUTTON = "#repo_create_button"
        REPO_NAME_FIELD = "#new_repo_name"
        SEARCH_BOX = "#repo_list_filter input"
        TABLE_BODY = "#body"
        TEST_FILE = "notebooks/" + self.test_filename
        UPLOAD_BUTTON = "#upload_button"

        driver = webdriver.Chrome() 
        driver.implicitly_wait(5)
        driver.get(self.app.display_url)

        KernelImageCreator.create = lambda x, y: IMAGE

        # remove the token from the url and specify a file to visit
        notebook_url = self.app.display_url.split("?")[0] + TEST_FILE
        driver.get(notebook_url)

        driver.find_element_by_css_selector(KERNEL_BUTTON).click()
        driver.find_element_by_id(CONTAINERIZE_OPTION).click()

        # verify expected UI elements are present
        EXPECTED_REPO_SELECT_MODAL_ELEMENTS = [REPO_CREATE_BUTTON, SEARCH_BOX, "#repo_list_next",
            "#repo_list_previous", "#repo_list_filter", "#repo_list_length label",
            ".modal-body", "#select_repo_cancel"]
        for expected_element in EXPECTED_REPO_SELECT_MODAL_ELEMENTS:
            self.assertEquals(1, len(driver.find_elements_by_css_selector(expected_element)))

        self.assertEquals(0, len(driver.find_elements_by_css_selector(LISTED_REPOS)))

        # create repos and verify they are listed/filtered properly
        driver.find_element_by_css_selector(REPO_CREATE_BUTTON).send_keys(Keys.RETURN);
        driver.find_element_by_css_selector(REPO_NAME_FIELD).send_keys(REPO1)
        driver.find_element_by_css_selector(CREATE_REPO_BUTTON).click()
        self.assertEquals(1, len(driver.find_elements_by_css_selector(LISTED_REPOS)))
        WebDriverWait(driver, 3).until(EC.invisibility_of_element_located((By.CSS_SELECTOR, CREATE_REPO_BUTTON)))
        driver.find_element_by_css_selector(REPO_CREATE_BUTTON).send_keys(Keys.RETURN);
        driver.find_element_by_css_selector(REPO_NAME_FIELD).send_keys(REPO2)
        driver.find_element_by_css_selector(CREATE_REPO_BUTTON).click()
        driver.find_element_by_css_selector(SEARCH_BOX).clear()
        driver.find_element_by_css_selector(SEARCH_BOX).send_keys("repo")
        self.assertEquals(2, len(driver.find_elements_by_css_selector(LISTED_REPOS)))

        # upload an image to a repository and verify docker recieved the upload request
        driver.find_element_by_css_selector(SEARCH_BOX).clear()
        driver.find_element_by_css_selector(SEARCH_BOX).send_keys(REPO1)
        driver.find_element_by_css_selector(TABLE_BODY).click()
        driver.find_element_by_css_selector(UPLOAD_BUTTON).click()
        self.assertEquals(1, len(driver.find_elements_by_css_selector(PROGRESS_BAR)))
        # give the backend time to receive the request
        time.sleep(1)
        ecr_client = boto3.client("ecr")
        repository_uri = ecr_client.describe_repositories(repositoryNames=[REPO1])["repositories"][0]["repositoryUri"]
        self.mock_docker.api.tag.assert_called_once_with(IMAGE + LATEST, repository=repository_uri + LATEST)
        auth_config = {"username": "AWS", "password": "us-east-1-auth-token"}
        self.mock_docker.api.push.assert_called_once_with(auth_config=auth_config, repository=repository_uri + LATEST, stream=True)

def main():
    current_directory = os.path.dirname(os.path.realpath(__file__))
    TestPlugin.app = NotebookApp(open_browser=False, notebook_dir=current_directory)
    TestPlugin.app.initialize()
    TestPlugin.mock_docker = MagicMock()

    io_loop = IOLoop.current()
    io_loop.call_later(1, _run_tests_in_thread)
    with patch("docker.from_env", return_value=TestPlugin.mock_docker):
        TestPlugin.app.start()
 
def _run_tests_in_thread():
    thread = threading.Thread(target=unittest.main)
    thread.start()

if __name__ == "__main__":
    main()

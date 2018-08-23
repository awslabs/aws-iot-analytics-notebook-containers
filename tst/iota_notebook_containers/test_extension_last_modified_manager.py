import boto3
import datetime
import itertools
import moto
import os
import unittest
import tempfile

from unittest.mock import patch, MagicMock

from iota_notebook_containers.extension_last_modified_manager import ExtensionLastModifiedManager, EXTENSION_BUCKET, EXTENSION_KEY

class TestExtensionLastModifiedManager(unittest.TestCase):
	def setUp(self):
		self.extension_last_modified_manager = ExtensionLastModifiedManager()
		self.last_modified_date = "81534470005.0"

	@moto.mock_s3
	def test_GIVEN_file_on_s3_WHEN_get_s3_extension_last_modified_date_THEN_return_file_last_modified(self):
		# GIVEN
		modified_datetime = datetime.datetime.fromtimestamp(int(float(self.last_modified_date)))
		s3_client = MagicMock()
		s3_client.get_object = lambda **kwargs: {"LastModified": modified_datetime}

		# WHEN
		with patch("boto3.client", return_value=s3_client):
			observed = self.extension_last_modified_manager.get_s3_extension_last_modified_date()

		# THEN
		self.assertEquals(self.last_modified_date, observed)

	def test_GIVEN_date_WHEN_save_last_modified_date_to_file_THEN_save_date_to_file(self):
		# GIVEN
		with tempfile.NamedTemporaryFile() as temp_file:
			date_file = temp_file.name
			self.extension_last_modified_manager.last_modification_time_filepath = date_file

			# WHEN
			self.extension_last_modified_manager.save_last_modified_date_to_file(self.last_modified_date)

			# THEN
			with open(date_file, "r") as f:
				date_file_contents = f.read()
			self.assertEquals(self.last_modified_date, date_file_contents)

	def test_GIVEN_date_in_file_WHEN_test_get_local_extension_modified_date_THEN_return_date(self):
		# GIVEN
		with tempfile.NamedTemporaryFile() as temp_file:
			date_file = temp_file.name
			self.extension_last_modified_manager.last_modification_time_filepath = date_file
			with open(date_file, "w") as f:
				f.write(self.last_modified_date)

			# WHEN
			observed = self.extension_last_modified_manager.get_local_extension_modified_date()

			# THEN
			self.assertEquals(self.last_modified_date, observed)

if __name__ == '__main__':
    unittest.main()
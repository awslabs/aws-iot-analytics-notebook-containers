import boto3
import os
import pathlib

EXTENSION_BUCKET = "iotanalytics-notebook-containers"
EXTENSION_KEY = "iota_notebook_containers.zip"

class ExtensionLastModifiedManager(object):
	def __init__(self):
		current_file = os.path.realpath(__file__)
		self.last_modification_time_filepath = os.path.join(pathlib.Path.home(), ".iota_notebook_containers_last_modified")

	def get_s3_extension_last_modified_date(self):
		s3_client = boto3.client("s3")
		extension_object = s3_client.get_object(Bucket=EXTENSION_BUCKET, Key=EXTENSION_KEY)
		return str(extension_object["LastModified"].timestamp())

	def save_last_modified_date_to_file(self, last_modified_date):
		with open(self.last_modification_time_filepath, "w") as f:
			f.write(last_modified_date)

	def get_local_extension_modified_date(self):
		with open(self.last_modification_time_filepath, "r") as f:
			return f.read()

if __name__ == '__main__':
	extension_last_modified_manager = ExtensionLastModifiedManager()
	last_modified_date = extension_last_modified_manager.get_s3_extension_last_modified_date()
	extension_last_modified_manager.save_last_modified_date_to_file(last_modified_date)
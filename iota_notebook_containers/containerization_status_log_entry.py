import json
import os
import time

from iota_notebook_containers.constants import SAGEMAKER_FOLDER

class ContainerizationStatusLogEntry(object):
    IMAGE_CREATION_STEP = "image_creation"
    IMAGE_UPLOAD_STEP = "image_upload"
    VERSION = "1.0.0"
    def __init__(self, notebook_path, step=None, notebook_modification_time=None, progress=None, error_msg=None, error_trace=None, containerization_start=None):
        if step not in [self.IMAGE_CREATION_STEP, self.IMAGE_UPLOAD_STEP]:
            raise RuntimeError("{} is not a valid step.".format(step))

        self.notebook_path = self.to_relative_notebook_path(notebook_path)
        self.step = step
        self.epoch_timestamp = time.time()
        self.notebook_modification_time = notebook_modification_time
        self.progress = progress
        self.error_msg = error_msg
        self.error_trace = error_trace
        self.containerization_start = containerization_start
        self.version = ContainerizationStatusLogEntry.VERSION

    @classmethod
    def of_image_creation(cls, notebook_path, **kwargs):
        return cls(notebook_path, step=cls.IMAGE_CREATION_STEP, **kwargs)

    @classmethod
    def of_image_upload(cls, notebook_path, **kwargs):
        return cls(notebook_path, step=cls.IMAGE_UPLOAD_STEP, **kwargs)

    @classmethod
    def to_relative_notebook_path(cls, notebook_path):
        if notebook_path and notebook_path.startswith(SAGEMAKER_FOLDER + '/'):
            return os.path.relpath(notebook_path, SAGEMAKER_FOLDER)
        return notebook_path

    def as_dict(self):
        log_entry = {}
        log_entry["notebook_path"] = self.notebook_path
        log_entry["epoch_timestamp"] = self.epoch_timestamp
        log_entry["step"] = self.step
        log_entry["notebook_modification_time"] = self.notebook_modification_time
        log_entry["progress"] = self.progress
        log_entry["error_msg"] = self.error_msg
        log_entry["error_trace"] = self.error_trace
        log_entry["containerization_start"] = self.containerization_start
        log_entry["version"] = self.version
        return log_entry

    def __repr__(self):
        return json.dumps(self.as_dict())

    def __str__(self):
        return repr(self)

    def __eq__(self, other):
        if isinstance(other, ContainerizationStatusLogEntry):
            return self.as_dict() == other.as_dict()
        return NotImplemented

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(tuple(sorted(self.as_dict.items())))

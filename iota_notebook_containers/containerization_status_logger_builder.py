"""
Builds a logger for storing containerization status information
This information is then exposed to the console
"""

import logging
import os

class ContainerizationStatusLoggerBuilder(logging.Logger):
    CONTAINERIZATION_STATUS_EXTENSION = ".containerizer_log"

    @classmethod
    def build(cls, notebook_path):
        log_filepath = cls._get_log_path(notebook_path)
        logger = logging.getLogger(log_filepath)

        for handler in logger.handlers:
            handler.close()
            logger.removeHandler(handler)

        handler = logging.FileHandler(log_filepath, mode="w")
        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)

        return logger

    @classmethod
    def _get_log_path(cls, notebook_path):
        max_truncated_basename_length = 255 - len(cls.CONTAINERIZATION_STATUS_EXTENSION)
        notebook_basename_no_ext = os.path.splitext(os.path.basename(notebook_path))[0]
        log_basename = notebook_basename_no_ext[:max_truncated_basename_length] + cls.CONTAINERIZATION_STATUS_EXTENSION
        log_filepath = os.path.join(os.path.dirname(notebook_path), log_basename)
        return log_filepath

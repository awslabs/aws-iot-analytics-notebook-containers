
import unittest

from iota_notebook_containers.containerization_status_logger_builder import ContainerizationStatusLoggerBuilder

class TestContainerizationStatusLoggerBuilder(unittest.TestCase):
    def test_GIVEN_short_path_WHEN_get_log_path_THEN_just_change_extension(self):
        notebook_path = "/home/ec2_user/Sagemaker/mynotebook.ipynb"
        expected = notebook_path = "/home/ec2_user/Sagemaker/mynotebook.containerizer_log"
        observed = ContainerizationStatusLoggerBuilder._get_log_path(notebook_path)
        self.assertEqual(expected, observed)

    def test_GIVEN_long_path_WHEN_get_log_path_THEN_truncate_filename(self):
        notebook_path = "/home/ec2_user/Sagemaker/" + 249 * "a" + ".ipynb" 
        expected = notebook_path = "/home/ec2_user/Sagemaker/" + 237 * "a" + ".containerizer_log"
        observed = ContainerizationStatusLoggerBuilder._get_log_path(notebook_path)
        self.assertEqual(expected, observed)

if __name__ == '__main__':
    unittest.main()

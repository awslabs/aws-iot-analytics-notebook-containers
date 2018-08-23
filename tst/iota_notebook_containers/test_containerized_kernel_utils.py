import unittest

from iota_notebook_containers.containerized_kernel_utils import remove_containerized_prefix

class TestContainerizedKernelUtils(unittest.TestCase):

    def test_GIVEN_name_without_containerized_prefix_WHEN_remove_prefix_THEN_return_unmodified_kernel_name(self):
        kernel_name = "conda_python3"
        self.assertEqual(kernel_name, remove_containerized_prefix(kernel_name))

    def test_GIVEN_name_with_containerized_prefix_WHEN_remove_prefix_THEN_return_without_prefix(self):
        with_prefix = "containerized_conda_python3"
        without_prefix = "conda_python3"
        self.assertEqual(without_prefix, remove_containerized_prefix(with_prefix))

if __name__ == '__main__':
    unittest.main()

import itertools
import os
import unittest

from unittest.mock import patch, MagicMock

from iota_notebook_containers.kernel_image_creator import KernelImageCreator

class TestKernelImageCreator(unittest.TestCase):
    def test_GIVEN_emtpy_list_WHEN_get_message_if_space_insufficientv_THEN_none(self):
        self.assertEquals(None, KernelImageCreator._get_message_if_space_insufficient([]))

    def test_GIVEN_suffient_space_WHEN_get_message_if_space_insufficient_THEN_none(self):
        with patch("os.path.getsize", return_value=1):
            self.assertEquals(None,
                KernelImageCreator._get_message_if_space_insufficient(["file", "other_file"]))

    def test_GIVEN_insuffient_space_WHEN_get_message_if_space_insufficient_THEN_msg(self):
        # GIVEN
        size_of_each_file = 100
        free_space = 10
        files = ["file", "other_file"]

        # WHEN
        with patch("os.path.getsize", return_value=size_of_each_file):
            with patch("shutil.disk_usage", return_value=(None, None, free_space)):
                observed = KernelImageCreator._get_message_if_space_insufficient(files)

        # THEN
        total_bytes_needed = len(
            files) * size_of_each_file + KernelImageCreator.SPACE_REQUIREMENT_FUDGE_BYTES
        expected = "This instance has insufficient free space to run containerization. " + \
            "It has 10 bytes, but it needs {} bytes.".format(total_bytes_needed)
        self.assertEquals(expected, observed)

    def test_remove_prefix_with_prefix_present(self):
        self.assertEquals("text", KernelImageCreator._remove_prefix("prefix_text", "prefix_"))

    def test_remove_prefix_without_prefix_present(self):
        self.assertEquals("text", KernelImageCreator._remove_prefix("text", "prefix_"))

    def test_generate_files_to_copy(self):
        # GIVEN
        filenames = ["file1", "a_file2", "file3.pyc"]
        input_paths = [os.path.realpath(f) for f in filenames]

        # WHEN
        with patch("os.walk", return_value=[("/", None, input_paths)]):
            with patch("os.path.exists", return_value=True):
                observed_output = [f for f in KernelImageCreator._generate_files_to_copy(["irrelevant"], KernelImageCreator.EXCLUDE_FROM_CP)]
        
        # THEN
        filtered_filenames = ["a_file2", "file1"]
        expected_output = ["/home/ec2-user/iota_run_nb.py"] + [os.path.realpath(f) for f in filtered_filenames]
        self.assertEquals(expected_output, observed_output)

    def test_get_child_path_only_one_distinct(self):
        # GIVEN
        root = "/root/folder"
        folder1 = "/root/folder/subfolder/folder1"
        folder2 = "/root/folder/folder2"
        folders = [root, folder1, folder2]

        # WHEN/THEN
        for permutation in itertools.permutations(folders):
            self.assertCountEqual([folder1, folder2], KernelImageCreator._get_child_paths(permutation))

    def test_get_child_path_two_distinct(self):
        # GIVEN
        root1 = "/root/folder"
        root2 = "/root/other_folder"
        folder1 = "/root/folder/subfolder/folder1"
        folder2 = "/root/other_folder/folder2"
        folders = [root1, root2, folder1, folder2]

        # WHEN/THEN
        for permutation in itertools.permutations(folders):
            self.assertCountEqual([folder1, folder2], KernelImageCreator._get_child_paths(permutation))

    def test_split_into_batches_1_batch(self):
        # GIVEN
        files = ["file1", "file2", "file3"]

        # WHEN
        with patch("os.path.getsize", return_value=KernelImageCreator.MAX_FILEBATCH_SIZE/4):
            batches = [batch for batch in KernelImageCreator._split_into_batches(files)]

        # THEN
        self.assertEquals(1, len(batches))
        self.assertCountEqual(files, batches[0])

    def test_split_into_batches_2_batches(self):
        # GIVEN
        files = ["file1", "file2", "file3"]

        # WHEN
        with patch("os.path.getsize", return_value=KernelImageCreator.MAX_FILEBATCH_SIZE/2):
            batches = [batch for batch in KernelImageCreator._split_into_batches(files)]

        # THEN
        self.assertEquals(2, len(batches))
        self.assertCountEqual(files[:2], batches[0])
        self.assertCountEqual([files[2]], batches[1])

    def test_copy_onto_containers(self):
        # GIVEN
        files = ["folder1/file1", "folder2/file2", "folder3/file3"]
        interim_container = MagicMock()
        tarstream = MagicMock()

        # WHEN
        with patch("tarfile.TarFile.__enter__", return_value=tarstream):
            KernelImageCreator._copy_onto_container(interim_container, files)

        # THEN
        for f in files:
            tarstream.add.assert_any_call(f)
        self.assertEquals(len(files), tarstream.add.call_count)

if __name__ == '__main__':
    unittest.main()

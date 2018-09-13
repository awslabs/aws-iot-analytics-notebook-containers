import json
import os
import unittest
from mock import patch, mock_open, MagicMock

class TestNotebookRunner(unittest.TestCase):

    @patch("docker.from_env", MagicMock())
    @patch("boto3.resource", MagicMock())
    def test_GIVEN_params_and_notebook_WHEN_run_notebook_THEN_verify_output_notebook(self):
        expected_output_file_path = os.path.join(os.path.dirname(__file__), 'resources', 'output.ipynb')
        with open(expected_output_file_path) as f:
            expected = json.dumps(json.load(f), sort_keys=True)
            params = self._get_params_for_test()
            with patch("builtins.open", mock_open(read_data='')):
                with patch("json.load", MagicMock(return_value=params)):
                    from iota_notebook_containers import iota_run_nb
                    test_context = iota_run_nb.Context()
                    iota_run_nb._replace_variables_in_notebook(test_context)
                    actual = json.dumps(test_context.nb, sort_keys=True)
                    self.assertEqual(expected, actual)

    def _get_params_for_test(self):
        params_file_path = os.path.join(os.path.dirname(__file__), 'resources', 'params')
        notebook_file_path = os.path.join(os.path.dirname(__file__), 'resources', 'notebook.ipynb')
        with open(params_file_path) as params_file:
            params = json.load(params_file)
            params['Context']['Analysis'] = notebook_file_path
        return params

if __name__ == '__main__':
    unittest.main()
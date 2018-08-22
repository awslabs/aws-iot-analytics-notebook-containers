import unittest

from iota_notebook_containers.export_to_ecr_params_validator import ImageCreationAndUploadParamsValidator, \
    REQUIRED_INPUT_PARAMS, MAX_NUM_VARIABLES

class TestCreateNewRepoHandler(unittest.TestCase):
    REPO_NAME = "test_repo"
    def setUp(self):
        super().setUp()
        self.input_params = {
            "container_name": "name",
            "container_description": "desc",
            "notebook_path": "some_path",
            "kernel_name": "containerized_conda_python3",
            "variables": [{"name": "valid_name", "type": "string", "description": ""}],
            "repository_name": self.REPO_NAME
        }

    def test_GIVEN_valid_input_WHEN_get_invalid_params_msg_THEN_return_none(self):
        observed = yield ImageCreationAndUploadParamsValidator.get_invalid_params_msg(self.input_params)
        self.assertFalse(observed)

    def test_GIVEN_missing_field_WHEN_get_invalid_params_msg_THEN_return_msg(self):
        for field in REQUIRED_INPUT_PARAMS:
            input_params = dict(self.input_params)
            del input_params[field]
            observed_msg = yield ImageCreationAndUploadParamsValidator.get_invalid_params_msg(input_params)
            expected_msg = "The following fields were not specified: {}.".format(field)
            self.assertEqual(expected_msg, observed_msg)

    def test_GIVEN_duplicate_variable_name_WHEN_get_invalid_params_msg_THEN_return_msg(self):
        # GIVEN
        var = {"name": "duplicate_name", "type": "string", "description": ""}
        self.input_params["variables"].extend([var, var])

        # WHEN
        observed_msg = yield ImageCreationAndUploadParamsValidator.get_invalid_params_msg(self.input_params)

        # THEN
        expected_msg = "Each variable must have a name that's different from the others."
        self.assertEqual(expected_msg, observed_msg)

    def test_GIVEN_invalid_variable_name_WHEN_get_invalid_params_msg_THEN_return_msg(self):
        NAMES = ["a" * 1000, "", None]
        for name in NAMES:
            self.input_params["variables"][0]["name"] = name
            observed_msg = yield ImageCreationAndUploadParamsValidator.get_invalid_params_msg(self.input_params)
            expected_msg = "This variable name is not valid: {}.".format(name)
            self.assertTrue(expected_msg, observed_msg)

    def test_GIVEN_too_long_container_name_WHEN_get_invalid_params_msg_THEN_return_msg(self):
        # GIVEN
        name = "a" * 10000
        self.input_params["container_name"] = name

        # WHEN
        observed_msg = yield ImageCreationAndUploadParamsValidator.get_invalid_params_msg(self.input_params)

        # THEN
        expected_msg = "The container name is longer than the 512 character maximum."
        self.assertEqual(expected_msg, observed_msg)

    def test_GIVEN_no_container_name_WHEN_get_invalid_params_msg_THEN_return_msg(self):
        NAMES = ["", None]
        for name in NAMES:
            self.input_params["container_name"] = name
            observed_msg = yield ImageCreationAndUploadParamsValidator.get_invalid_params_msg(self.input_params)
            expected_msg = "The container name must be defined."
            self.assertEqual(expected_msg, observed_msg)

    def test_GIVEN_invalid_variable_type_WHEN_get_invalid_params_msg_THEN_return_msg(self):
        VARIABLE_TYPES = ["blarg", "", None]
        for var_type in VARIABLE_TYPES:
            self.input_params["variables"][0]["type"] = var_type
            observed_msg = yield ImageCreationAndUploadParamsValidator.get_invalid_params_msg(self.input_params)
            expected_msg = "The variable valid_name has an invalid type."
            self.assertEqual(expected_msg, observed_msg)

    def test_GIVEN_invalid_variable_desc_WHEN_get_invalid_params_msg_THEN_return_msg(self):
        # GIVEN
        self.input_params["variables"][0]["description"] = "a" * 10000

        # WHEN
        observed_msg = yield ImageCreationAndUploadParamsValidator.get_invalid_params_msg(self.input_params)

        # THEN
        expected_msg = "The variable valid_name's description is longer than the 5120 character maximum."
        self.assertEqual(expected_msg, observed_msg)

    def test_GIVEN_invalid_container_desc_WHEN_get_invalid_params_msg_THEN_return_msg(self):
        # GIVEN
        self.input_params["container_description"] = "a" * 10000

        # WHEN
        observed_msg = yield ImageCreationAndUploadParamsValidator.get_invalid_params_msg(self.input_params)

        # WHEN
        expected_msg = "The container description is longer than the 5120 character maximum."
        self.assertEqual(expected_msg, observed_msg)

    def test_GIVEN_invalid_kernel_name_WHEN_get_invalid_params_msg_THEN_return_msg(self):
        # GIVEN
        self.input_params["kernel_name"] = "conda_python3"

        # WHEN
        observed_msg = yield ImageCreationAndUploadParamsValidator.get_invalid_params_msg(self.input_params)

        # THEN
        self.assertEqual('Only kernels beginning with "containerized" may be containerized.',
            observed_msg)

    def test_GIVEN_invalid_python_identifiers_in_var_name_WHEN_get_invalid_params_msg_THEN_return_msg(self):
        # GIVEN
        self.input_params["variables"][0]["name"] = "@hi"

        # WHEN
        observed_msg = yield ImageCreationAndUploadParamsValidator.get_invalid_params_msg(self.input_params)

        # THEN
        expected_msg = "The following names are not valid python identifiers: @hi."
        self.assertEqual(expected_msg, observed_msg)

    def test_GIVEN_too_many_variables_WHEN_get_invalid_params_msg_THEN_return_msg(self):
        # GIVEN
        for i in range(MAX_NUM_VARIABLES):
            var = {"name": "a" * i, "type": "double", "description": ""}
            self.input_params["variables"].append(var)

        # WHEN
        observed_msg = yield ImageCreationAndUploadParamsValidator.get_invalid_params_msg(self.input_params)

        # THEN
        self.assertEqual("You may only specify at most 50 variables.", observed_msg)

if __name__ == '__main__':
    unittest.main()
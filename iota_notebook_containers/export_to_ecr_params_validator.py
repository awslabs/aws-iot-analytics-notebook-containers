CONTAINERIZED_PREFIX = "containerized_" 
REQUIRED_INPUT_PARAMS = ["notebook_path", "kernel_name", "variables", "container_name",
    "container_description", "repository_name"]
MAX_NUM_VARIABLES = 50
MAX_VARIABLE_NAME_LENGTH = 256
MAX_VARIABLE_DESCRIPTION_LENGTH = 1024
VARIABLE_TYPES = ["string", "double", "outputFileUri", "datasetContentVersionId"] 

def _missing_or_bad_length_msg(prefix, obj, field, must_be_present, max_length):
    if not obj.get(field, None):
        if must_be_present:
            return "{} must be defined.".format(prefix)

    elif max_length and len(obj[field]) > max_length:
        return "{} is longer than the {} character maximum.".format(prefix, max_length)

def _get_missing_fields_msg(input_params):
    missing_fields = [field for field in REQUIRED_INPUT_PARAMS if field not in input_params]
    if missing_fields:
        return "The following fields were not specified: {}.".format(", ".join(
            sorted(missing_fields)))

def _get_invalid_kernel_name_msg(input_params):
    if not input_params["kernel_name"].lower().startswith(CONTAINERIZED_PREFIX):
        return 'Only kernels beginning with "{}" may be containerized.'.format(
            CONTAINERIZED_PREFIX.strip("_"))

def _get_bad_container_name_msg(input_params):
    prefix = "The container name"
    return _missing_or_bad_length_msg(
        prefix, input_params, "container_name", True, MAX_VARIABLE_NAME_LENGTH)

def _get_bad_container_desc_msg(input_params):
    prefix = "The container description"
    return _missing_or_bad_length_msg(prefix,
        input_params, "container_description", False, MAX_VARIABLE_DESCRIPTION_LENGTH)

def _get_too_many_variables_msg(input_params):
    if input_params["variables"] and len(input_params["variables"]) > MAX_NUM_VARIABLES:
        return "You may only specify at most {} variables.".format(MAX_NUM_VARIABLES)

# this validator should be run before the type/description validators because those
# validators refer to variable names in their error messages.
def _get_invalid_variable_name_msg(input_params):
    variables = input_params["variables"]
    for variable in variables:
        if not variable.get("name", None):
            return "All variables must have a name that's at least one character long."
        prefix = "The variable name {}".format(variable["name"])
        bad_var_name_msg = _missing_or_bad_length_msg(
            prefix, variable, "name", False, MAX_VARIABLE_NAME_LENGTH)
        if bad_var_name_msg:
            return bad_var_name_msg

    if len(set(var["name"] for var in variables)) < len(variables):
        return "Each variable must have a name that's different from the others."

    invalid_python_var_names = [var["name"] for var in input_params["variables"]
        if not var["name"].isidentifier()]
    if invalid_python_var_names:
        return "The following names are not valid python identifiers: {}.".format(
            ", ".join(sorted(invalid_python_var_names)))

def _get_invalid_variables_type_msg(input_params):
    for variable in input_params["variables"]:
        if not variable["type"] or variable["type"] not in VARIABLE_TYPES:
            return "The variable {} has an invalid type.".format(variable["name"])

def _get_invalid_variables_desc_msg(input_params):
    for variable in input_params["variables"]:
        prefix = "The variable {}'s description".format(variable)
        bad_var_desc_msg = _missing_or_bad_length_msg(
            prefix, variable, "description", False, MAX_VARIABLE_DESCRIPTION_LENGTH)
        if bad_var_desc_msg:
            return bad_var_desc_msg


INVALID_PARAM_MSG_CREATION_FUNCTIONS = (_get_missing_fields_msg,
    _get_invalid_kernel_name_msg, _get_bad_container_name_msg, 
    _get_bad_container_desc_msg, _get_too_many_variables_msg,
    _get_invalid_variable_name_msg, _get_invalid_variables_type_msg,
    _get_invalid_variables_desc_msg)


class ImageCreationAndUploadParamsValidator(object):
    @staticmethod
    async def get_invalid_params_msg(input_params):
        for invalid_param_msg_fun in INVALID_PARAM_MSG_CREATION_FUNCTIONS:
            invalid_param_msg = invalid_param_msg_fun(input_params)
            if invalid_param_msg:
                return invalid_param_msg



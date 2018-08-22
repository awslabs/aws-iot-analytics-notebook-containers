import json
import tornado

from IPython import get_ipython
from IPython.core.magics.namespace import NamespaceMagics

# we don't have to worry about this dict polluting the namespace because
# dicts are not one of the returned types
PYTHON_TYPE_TO_IOT_TYPE = {
    "str": "string",
    "NoneType": "string",
    "int": "double",
    "float": "double",
    "long": "double"
}

def _list_kernel_vars():
    _nms = NamespaceMagics()
    _Jupyter = get_ipython()
    _nms.shell = _Jupyter.kernel.shell

    variables = [v for v in _nms.who_ls() if _get_var_type(v) in PYTHON_TYPE_TO_IOT_TYPE]
    return json.dumps([{'varName': v, 'varType': PYTHON_TYPE_TO_IOT_TYPE[_get_var_type(v)]}
    	for v in variables])

def _get_var_type(var):
	return type(eval(var)).__name__
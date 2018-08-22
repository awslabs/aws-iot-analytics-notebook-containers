import os
import ast
import asttokens
import json
import boto3
import nbformat
import uuid
from jupyter_client.kernelspec import KernelSpecManager
from six.moves.urllib.parse import urlparse
from nbconvert.preprocessors import ExecutePreprocessor
from nbconvert import HTMLExporter

IPYTHON_COMMAND_PREFIX_REPLACEMENT = 'pass#' + str(uuid.uuid4())
IPYTHON_COMMAND_PREFIX = ['%','!']

def _get_default_kernel_name():
    return next(iter(KernelSpecManager().find_kernel_specs().keys()))

class Context(object):
    def __init__(self):
        with open('/opt/ml/input/data/iotanalytics/params') as params_file:
            params = json.load(params_file)
        self.variables = params['Variables']
        context = params['Context']
        notebook_path = context.get('Analysis', os.environ.get('NOTEBOOK_PATH'))
        with open(notebook_path) as f:
            self.nb = nbformat.read(f, as_version=nbformat.NO_CONVERT)
        self.notebook_dir  = os.path.dirname(notebook_path)
        self.variables = params['Variables']
        output_uris = context['OutputUris']
        self.output_ipynb_s3_uri = output_uris['ipynb']
        self.output_html_s3_uri = output_uris['html']
        self.kernel_name = os.environ.get('KERNEL_NAME', _get_default_kernel_name())
        self.s3 = boto3.resource('s3')

class _Assignment(object):
    def __init__(self, ast_node):
        self.var_name = ast_node.targets[0].id
        self.val_startpos = ast_node.value.first_token.startpos
        self.val_endpos = ast_node.value.last_token.endpos

def _is_var_assigment(node):
    return (isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name))

def _sorted_assignments(source):
    tokens = asttokens.ASTTokens(source, parse=True)
    assignments = (_Assignment(n) for n in ast.walk(tokens.tree) if _is_var_assigment(n))
    return sorted(assignments, key = lambda a: a.val_startpos)

def _source_fragments_after_replacements(source, variables):
    last_val_endpos = 0;
    for a in _sorted_assignments(source):
        yield source[last_val_endpos:a.val_startpos]
        last_val_endpos = a.val_endpos
        original_val = source[a.val_startpos:a.val_endpos]
        yield repr(variables.pop(a.var_name)) if a.var_name in variables else original_val
    yield source[last_val_endpos:len(source)]

def _replace_variables(source, variables):
    return ''.join(_source_fragments_after_replacements(source, variables))

def _replace_variables_in_notebook(context):
    for cell in context.nb.cells:
        if cell.cell_type == 'code':
            try:
                source = _pre_handle_ipython_commands(cell.source)
                source = _replace_variables(source, context.variables)
                cell.source = _post_handle_ipython_commands(source)
            except (SyntaxError, ValueError) as e:
                pass # Continue to replace variables in other cells

def _replace_ipython_command(line):
    if _is_ipython_command(line):
        first_non_whitespace_character = line.lstrip()[0]
        return line.replace(first_non_whitespace_character, IPYTHON_COMMAND_PREFIX_REPLACEMENT + first_non_whitespace_character, 1)
    return line

def _is_ipython_command(line):
    line_without_leading_whitespace = line.lstrip()
    for mark in IPYTHON_COMMAND_PREFIX:
        if not line_without_leading_whitespace.startswith(mark + mark) and line_without_leading_whitespace.startswith(mark):
            return True
    return False

def _pre_handle_ipython_commands(source):
    return ''.join(_replace_ipython_command(line) for line in source.splitlines(True))

def _post_handle_ipython_commands(source):
    return source.replace(IPYTHON_COMMAND_PREFIX_REPLACEMENT,'')

def _write_to_s3(s3_uri, text, s3):
    url = urlparse(s3_uri)
    bucket = url.netloc
    key = url.path[1:]
    s3.Object(bucket, key).put(Body=text.encode('utf-8'), ACL='bucket-owner-full-control')

def _write_output_to_s3(context):
    ipynb_json = nbformat.writes(context.nb)
    _write_to_s3(context.output_ipynb_s3_uri, ipynb_json, context.s3)
    basic_html, _ = HTMLExporter(template_file='basic').from_notebook_node(context.nb)
    _write_to_s3(context.output_html_s3_uri, basic_html, context.s3)

def run_notebook(context=Context()):
    _replace_variables_in_notebook(context)

    try:
        ExecutePreprocessor(timeout=None, kernel_name=context.kernel_name).preprocess(
            context.nb, {'metadata': {'path': context.notebook_dir}})
    finally:
        _write_output_to_s3(context)

if __name__ == "__main__":
    run_notebook()

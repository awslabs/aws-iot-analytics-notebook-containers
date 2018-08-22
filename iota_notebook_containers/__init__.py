from notebook.utils import url_path_join

from iota_notebook_containers.export_to_ecr import CreateNewRepoHandler, ListRepoHandler, \
    UploadToRepoHandler, IsContainerizationOngoingHandler
from iota_notebook_containers.internal_log import create_logger

create_logger(__name__)

def _jupyter_server_extension_paths():
    return [{
        "module": "iota_notebook_containers"
    }]

def _jupyter_nbextension_paths():
    return [dict(
        section="notebook",
        src="static",
        dest="iota_notebook_containers",
        require="iota_notebook_containers/index")]

def load_jupyter_server_extension(nb_server_app):
    web_app = nb_server_app.web_app
    host_pattern = '.*$'
    web_app.add_handlers(host_pattern, [
        (url_path_join(web_app.settings['base_url'], r'/create_repo'), CreateNewRepoHandler), 
        (url_path_join(web_app.settings['base_url'], r'/upload_to_repo'), UploadToRepoHandler), 
        (url_path_join(web_app.settings['base_url'], r'/upload_to_repo/is_ongoing'),
            IsContainerizationOngoingHandler),
        (url_path_join(web_app.settings['base_url'], r'/list_repos'), ListRepoHandler)
    ])

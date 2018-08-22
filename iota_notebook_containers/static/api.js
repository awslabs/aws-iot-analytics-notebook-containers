define([
  "base/js/namespace",
  "jquery",
  "base/js/utils",
], function(Jupyter, $, utils){
  var CREATE_REPO_ENDPOINT = "create_repo";
  var IS_CONTAINERIZATION_ONGOING_ENDPOINT = "upload_to_repo/is_ongoing";
  var LIST_REPOS_ENDPOINT = "list_repos";
  var UPLOAD_TO_REPO_ENDPOINT = "upload_to_repo";

  var KERNEL_NAME_FIELD = "kernel_name";
  var NEXT_TOKEN_FIELD = "next_token";
  var NOTEBOOK_PATH_FIELD = "notebook_path";
  var REPO_NAME_FIELD = "repository_name";
  var TOKEN_FIELD = "_xsrf";

  var TOKEN_REGEX = "([^;]+)";
  var WEB_SOCKET_PROTOCOL = "wss://";

  // image creation/upload status fields
  var CURRENT_PROGRESS_FIELD = "progress";
  var ERROR_FIELD = "error_msg";
  var PROGRESS_DATA_FIELD = "data";

  var baseUrl = utils.get_body_data("baseUrl");

  function getToken(name){
    match = document.cookie.match(new RegExp(TOKEN_FIELD + "=" + TOKEN_REGEX));
    if (match){
      return match[1];
    }
  };

  function createRepo(repoName){
    var token = getToken();
    var requestUrl = utils.url_path_join(baseUrl, CREATE_REPO_ENDPOINT);
    return $.post(requestUrl, TOKEN_FIELD + "=" + token + "&" + REPO_NAME_FIELD + "=" + repoName);
  };

  function getRepos(next_token){
    var requestUrl = utils.url_path_join(baseUrl, LIST_REPOS_ENDPOINT);
    payload = next_token === null ? {} : {NEXT_TOKEN_FIELD: next_token};
    return $.getJSON(requestUrl, payload);
  };

  function isContainerizationOngoing(){
    var requestUrl = utils.url_path_join(baseUrl, IS_CONTAINERIZATION_ONGOING_ENDPOINT);
    return $.getJSON(requestUrl);
  };

  function uploadToRepo(repoName, variables, containerName, containerDescription, onMessage, onError, onClose){
    var requestUrl = WEB_SOCKET_PROTOCOL + utils.url_path_join(location.host, baseUrl, UPLOAD_TO_REPO_ENDPOINT);
    ws = new WebSocket(requestUrl);
    ws.onopen = function(evt){
      payload = {};
      payload[REPO_NAME_FIELD] = repoName;
      payload["variables"] = variables;
      payload["container_name"] = containerName;
      payload["container_description"] = containerDescription;
      payload[KERNEL_NAME_FIELD] = Jupyter.notebook.kernel["name"];
      payload[NOTEBOOK_PATH_FIELD] = Jupyter.notebook.notebook_path;
      ws.send(JSON.stringify(payload));
    };

    ws.onerror = onError;
    ws.onclose = onClose;
    ws.onmessage = function(response){uploadToRepoOnMessage(onMessage, response)};
  };

  function uploadToRepoOnMessage(onMessage, response){
    progressData = JSON.parse(response[PROGRESS_DATA_FIELD]);
    onMessage(progressData["step"], progressData["progress"], progressData["error_msg"]);
  };

  function listVariables(handleVariables) {
    var codeUrl = Jupyter.notebook.base_url + "nbextensions/iota_notebook_containers/list_variables.py";
    $.get(codeUrl).done(function(code) {
      Jupyter.notebook.kernel.execute(code, { iopub: { output: function(_) {} } }, { silent: false });
      Jupyter.notebook.kernel.execute('print(_list_kernel_vars())', { iopub: { output: function(msg) {
        var variables = msg.content['text'];
        if (!variables) {
          variables = '[]'
        }
        var jsonVars = JSON.parse(variables);
        handleVariables(jsonVars);
      } } }, { silent: false });
    })
  }

  return {createRepo: createRepo, getRepos: getRepos, uploadToRepo: uploadToRepo,
    listVariables: listVariables, isContainerizationOngoing: isContainerizationOngoing}
});
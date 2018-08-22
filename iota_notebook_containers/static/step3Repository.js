define([
  "base/js/dialog",
  "./api",
  "./createRepoMenu",
  "./progressBar",
  "./trim",
], function(dialog, api, createRepoMenu, progressBar, trim){
  var CREATE_REPO_BUTTON_ID = "step3_create_repo_button";
  var CREATE_REPO_SECTION_ID = "step3_create_repo_section";
  var CREATE_REPO_TEXTBOX_ID = "step3_create_repo_textbox";
  var ERROR_SECTION_ID = "step3_error_section"; 
  var REPO_TABLE_ID = "step3_repo_list";

  var NO_REPOSITORIES_MSG = "There are no matching repositories.";
  var DATATABLE_LANGUAGE = {
    "lengthMenu": "Display _MENU_ repositories per page",
    "zeroRecords": NO_REPOSITORIES_MSG,
    "info": "Showing _START_ to _END_ of _TOTAL_ repositories",
    "infoEmpty": "No repositories found.",
    "infoFiltered": "(filtered from _MAX_ total repositories)"
  };
  var DATATABLE_OPTIONS = "lfrtip";
  var DATATABLE_REPOS_PER_PAGE_SUFFIX = "_length";
  var DATATABLE_SEARCH_SUFFIX = "_filter";

  var HIDDEN_SELECTOR = ":hidden";
  var BODY_ROW_SELECTOR = "tbody tr";
  var SELECTED = "selected";
  var SELECTED_ROW_SELECTOR = "tr.selected";

  var CREATE_REPO_FAILURE_MSG = 'Failed to create repository. Please verify ' +
    'that the repository name complies with ECR requirements. If you ' + 
    'installed the containerization extension manually, please verify that ' + 
    'your Sagemaker Execution Role has access to AWS ECR.';
  var LIST_REPO_FAILED_MSG = 'Failed to fetch repositories. Please verify the ' + 
    'Sagemaker instance has sufficient ECR privleges.';

  var ID = "step3";
  var TAB_TITLE = "3. Select AWS ECR Repository";

  var CREATE_REPO_DIV_HTML = '' +
    '<div class="form-inline"> ' +
      '<div class="row form-group input-group"><label>' +
       '<span class="input-group" id="' + CREATE_REPO_SECTION_ID + '" ' +
          '<form><input type="text" id="' + CREATE_REPO_TEXTBOX_ID +
            '" placeholder="Repository Name"> ' +
          '</form>' + 
          '<button ' +
            'id="' + CREATE_REPO_BUTTON_ID + '">Create' + 
          '</button>' +
        '</span>' +
      '</div>' +
    '</div>';

  var FORM_HTML = '' + 
    '<div id="' + ID + '">' + 
      '<div class="input-group-btn" align="center">' +
      '</div>' +

      '<table id="' + REPO_TABLE_ID + '" class="table table-bordered" style="width:100%;word-wrap:break-word;">' +
          '<thead>' +
            '<tr>' +
              '<th>Name</th>' +
            '</tr>' +
          '</thead>' +
          '<tbody id="body"></tbody>' +
      '</table>' +
    '</div>' + 
    '<br> <div id="' + ERROR_SECTION_ID + '" class="alert alert-danger fade in">' + '</div>';

  function onModalOpen(nextButtonId){
    createTable();
    replaceReposPerPageWithRepoCreateButton();
    addPlaceholderToSearchBox();
    disableNext(nextButtonId);
    hideErrorSection();
    fillTable();

    $("#" + CREATE_REPO_BUTTON_ID).on("click", function(){
      createRepoOnClick(nextButtonId);
    });
    $("#" + REPO_TABLE_ID).on("click", BODY_ROW_SELECTOR, function(){
      rowOnClick(this, nextButtonId)
    });
    $("#" + nextButtonId).on("click", function(){
      if (! $("#" + nextButtonId).attr("disabled")) {
        hideErrorSection();
      }
    });
  };

  function rowOnClick(clicked, nextButtonId){
    if ($(clicked).hasClass(SELECTED)){
      $(clicked).removeClass(SELECTED);
      disableNext(nextButtonId);
    }
    else {
      $("#" + REPO_TABLE_ID + " " + SELECTED_ROW_SELECTOR).removeClass(SELECTED);
      $(clicked).addClass(SELECTED);
      var repository = getRepository();
      if (repository && repository.length !== 0){
        enableNext(nextButtonId);
      }
    }
  };

  function getRepository(){
    var repository = $("#" + REPO_TABLE_ID + " " + SELECTED_ROW_SELECTOR).text();
    // when there are no repositories, there is a row populated with a no
    // repositories message. if the user selected that row, that message will
    // get returned by the line above, but that message is not actually a repository.
    // this logic assumes that users cannot create a repository matching the
    // no repositories message.
    if (repository === NO_REPOSITORIES_MSG){
      return "";
    } else {
      return trim.trimValueIfPossible(repository);
    }
  };

  function createRepoOnClick(nextButtonId){
    $("#" + REPO_TABLE_ID + " " + SELECTED_ROW_SELECTOR).removeClass(SELECTED);
    disableNext(nextButtonId);    
    repoName = trim.trimValueIfPossible($("#" + CREATE_REPO_TEXTBOX_ID).val());
    if (! repoName){
      reportError("You must specify a repository name.");
    } else  {
      createRepo(repoName);
    }
  };

  function enableNext(nextButtonId){
    $("#" + nextButtonId).attr("disabled", false);
  }

  function disableNext(nextButtonId){
    $("#" + nextButtonId).attr("disabled", true);
  }

  function createRepo(repoName){
    $.when(api.createRepo(repoName)).then(
      function(){
        fadeOutErrorSection();
        addAndFilterForRepo(repoName);
      },
      function(){
        reportError(CREATE_REPO_FAILURE_MSG)
      });
  };

  function createTable(){
    this.dataTable = $("#" + REPO_TABLE_ID).DataTable({
      language: DATATABLE_LANGUAGE,
      dom: DATATABLE_OPTIONS,
    });
  };

  function fillTable(){
    function fillTableRecursive(next_token){
      $.when(api.getRepos(next_token)).then(function(response){
        addReposToTable(response.repositories);
        if (response.next_token !== null){
          fillTableRecursive(response.next_token);
        }
      }, function(response){reportError(LIST_REPO_FAILED_MSG)});
    };
    next_token = null;
    fillTableRecursive(next_token);
  };

  function addReposToTable(repos){
    for (i=0; i<repos.length; i++){
      this.dataTable.row.add([repos[i]]);
    }
    this.dataTable.draw();
  };

  function addAndFilterForRepo(repoName){
    this.dataTable.row.add([repoName]);
    this.dataTable.search(repoName).draw();
  };

  function replaceReposPerPageWithRepoCreateButton(){
    // replace the repos per page button with a create repo button
    // datatables supports a way to declaratively set custom button locations
    // but it relies on bootstrap having some font files that jupyter deleted
    // to save space. so, to create a button in our desired location, 
    // we created an element we didn't need and are now canabalizing its div
    $("#" + REPO_TABLE_ID + DATATABLE_REPOS_PER_PAGE_SUFFIX).html(CREATE_REPO_DIV_HTML);
  };

  function addPlaceholderToSearchBox(){
    $("#" + REPO_TABLE_ID + DATATABLE_SEARCH_SUFFIX).find(":input").attr(
      "placeholder", "Repository Name")
  };

  function hideErrorSection(){
    $("#" + ERROR_SECTION_ID).hide();
  };

    function fadeOutErrorSection(){
    $("#" + ERROR_SECTION_ID).fadeOut();
  };

  function reportError(error){
    $("#" + ERROR_SECTION_ID).text(error);
    $("#" + ERROR_SECTION_ID).fadeIn();
  };

return {ID: ID, FORM_HTML: FORM_HTML, TAB_TITLE: TAB_TITLE,
  onModalOpen: onModalOpen, getRepository: getRepository};
});
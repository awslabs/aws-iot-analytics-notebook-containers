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

  var DATATABLE_CURRENT_PAGE = "current";
  var DATATABLE_LANGUAGE = {
    "lengthMenu": "Display _MENU_ repositories per page",
    "zeroRecords": NO_REPOSITORIES_MSG,
    "info": "Showing _START_ to _END_ of _TOTAL_ repositories",
    "infoEmpty": "No repositories found.",
    "infoFiltered": "(filtered from _MAX_ total repositories)"
  };
  var DATATABLE_OPTIONS = "lfrtip";
  var DATATABLE_PAGE_LENGTH = 5;
  var DATATABLE_REPOS_PER_PAGE_SUFFIX = "_length";
  var DATATABLE_SEARCH_SUFFIX = "_filter";

  var HIDDEN_SELECTOR = ":hidden";
  var BODY_ROW_SELECTOR = "tbody tr";
  var SELECTED = "selected";
  var SELECTED_ROW_SELECTOR = "tr.selected";

  var PERMISSIONS_DOCUMENTATION_LINK = 'https://docs.aws.amazon.com/iotanalytics/latest/userguide/automate.html#aws-iot-analytics-automate-permissions';
  var PERMISSIONS_LINK_HTML = 'You can read about the required permissions ' +
    '<a class="alert-link" href="' + PERMISSIONS_DOCUMENTATION_LINK +'">here</a>.';
  var CREATE_REPO_FAILURE_HTML = 'Failed to create repository. Please verify ' +
    'that the repository name complies with AWS ECR requirements and that ' +
    'your SageMaker Execution Role provides access to AWS ECR. ' +
    PERMISSIONS_LINK_HTML;
  var LIST_REPO_FAILED_HTML = 'Failed to fetch repositories. Please verify that ' +
    'your SageMaker Execution Role provides access to AWS ECR. ' +
    PERMISSIONS_LINK_HTML;

  var DIFFERENT_REPOS_TEXT = "Please upload different notebooks to different repositories.";

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
      '<div class="alert alert-info"> ' + DIFFERENT_REPOS_TEXT + '</div>' +
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
    getOrCreateTable();
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

  function getSelectedRows(){
    return this.dataTable.rows(SELECTED_ROW_SELECTOR).nodes();
  };

  function clearSelectedRows(nextButtonId){
    var selectedRows = getSelectedRows();

    for (i=0; i<selectedRows.length; i++){
      $(selectedRows[i]).removeClass(SELECTED);
    }
    updateNextButtonStatus(nextButtonId);
  };

  function selectRow(row, nextButtonId){
    clearSelectedRows(nextButtonId);
    $(row).addClass(SELECTED);
    updateNextButtonStatus(nextButtonId);
  };

  function updateNextButtonStatus(nextButtonId){
    var repository = getRepository();
    if (repository && repository.length !== 0){
      enableNext(nextButtonId);
    } else{
      disableNext(nextButtonId);
    }
  };

  function rowOnClick(clicked, nextButtonId){
    var alreadySelected = $(clicked).hasClass(SELECTED);
    clearSelectedRows(nextButtonId);
    if (! alreadySelected){
      selectRow(clicked, nextButtonId);
    }
  };

  function getRepository(){
    var selectedRows = getSelectedRows();
    if (selectedRows.length > 0){
      var repository = $(selectedRows[0]).text();
      // when there are no repositories, there is a row populated with a no
      // repositories message. if the user selected that row, that message will
      // get returned by the line above, but that message is not actually a repository.
      // this logic assumes that users cannot create a repository matching the
      // no repositories message.
      if (repository !== NO_REPOSITORIES_MSG){
        return trim.trimValueIfPossible(repository);
      }
    }
    return "";
  };

  function createRepoOnClick(nextButtonId){
    clearSelectedRows(nextButtonId);
    disableNext(nextButtonId);    
    repoName = trim.trimValueIfPossible($("#" + CREATE_REPO_TEXTBOX_ID).val());
    if (! repoName){
      reportError("You must specify a repository name.");
    } else  {
      createRepo(repoName, nextButtonId);
    }
  };

  function enableNext(nextButtonId){
    $("#" + nextButtonId).attr("disabled", false);
  }

  function disableNext(nextButtonId){
    $("#" + nextButtonId).attr("disabled", true);
  }

  function createRepo(repoName, nextButtonId){
    $.when(api.createRepo(repoName)).then(
      function(){
        fadeOutErrorSection();
        addAndFilterForRepo(repoName);
        selectTopRowIfNoRowsSelected(nextButtonId);
      },
      function(){
        reportError(CREATE_REPO_FAILURE_HTML)
      });
  };

  function getOrCreateTable(){
    this.dataTable = $("#" + REPO_TABLE_ID).DataTable({
      language: DATATABLE_LANGUAGE,
      dom: DATATABLE_OPTIONS,
      pageLength: DATATABLE_PAGE_LENGTH,
      retrieve: true,
    });
    return this.dataTable;
  };

  function fillTable(){
    function fillTableRecursive(next_token){
      $.when(api.getRepos(next_token)).then(function(response){
        addReposToTable(response.repositories);
        if (response.next_token !== null){
          fillTableRecursive(response.next_token);
        }
      }, function(response){reportError(LIST_REPO_FAILED_HTML)});
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
    var repoRegex = "^" + repoName + "$";
    this.dataTable.search(repoRegex, {regex: true}).draw();
  };

  function selectTopRowIfNoRowsSelected(nextButtonId){
    // if a row hasn't been selected, select the first one
    // this makes the selection process more obvious without
    // risking losing the user's previous input
    if (! getRepository()){
      var dt = getOrCreateTable();
      var currentPageRows = dt.rows({page: DATATABLE_CURRENT_PAGE}).nodes();
      if (currentPageRows.length > 0){
        var row = currentPageRows[0];
        selectRow(row, nextButtonId);
      }
    }
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
    $("#" + ERROR_SECTION_ID).html(error);
    $("#" + ERROR_SECTION_ID).fadeIn();
  };

return {ID: ID, FORM_HTML: FORM_HTML, TAB_TITLE: TAB_TITLE,
  onModalOpen: onModalOpen, getRepository: getRepository, 
  selectTopRowIfNoRowsSelected: selectTopRowIfNoRowsSelected};
});
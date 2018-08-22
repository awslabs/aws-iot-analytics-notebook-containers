define([
    "base/js/dialog",
], function(dialog){
  var CREATE_REPO_BUTTON_ID = "create_repo_button"
  var CANCEL_BUTTON_ID = "create_repo_cancel";
  var FORM_ID = "create_repo_form";
  var MODAL_ID = "repo_name_modal";
  var NEW_REPO_NAME_ID = "new_repo_name";

  var MODAL_TITLE = "Enter Repository Name";

  var FORM_HTML = '' + 
    '<div id="' + FORM_ID + '">' +
      '<form role="form">' + 
        '<input id="' + NEW_REPO_NAME_ID + '" class="form-control" type="text" placeholder="Repository Name"/>'
      '</form>' + 
    '</div>'

  function launchModal(on_create){
    dialog.modal({
      id: MODAL_ID,
      title: MODAL_TITLE,
      body: $(FORM_HTML),
      open: onModalOpen,
      buttons: {
        Cancel: {id: CANCEL_BUTTON_ID},
        "Create Repository": {
          click: function(){
            var repoName = $("#" + NEW_REPO_NAME_ID).val();
            on_create(repoName);
          },
          class: "btn-primary",
          id: CREATE_REPO_BUTTON_ID
        }
      }
    });
  };

  function onModalOpen(){
    $("#" + CREATE_REPO_BUTTON_ID).attr("disabled", true);
    $("#" + NEW_REPO_NAME_ID).on("input", onFormChange);
  };

  function onFormChange(){
    if (!$("#" + NEW_REPO_NAME_ID).val().trim()){
      $("#" + CREATE_REPO_BUTTON_ID).attr("disabled", true);
    } else{
      $("#" + CREATE_REPO_BUTTON_ID).attr("disabled", false); 
    }
  };

    return {launchModal: launchModal}
});
define([
  "./trim",
], function(trim){
  var ID = "step1";
  var TAB_TITLE = "1. Name";

  var ERROR_SECTION_ID = "step1_error_section";
  var NAME_FIELD_ID = "step1_container_name";
  var DESCRIPTION_FIELD_ID = "step1_container_description_field";

  var MAX_NAME_LENGTH = 256;
  var MAX_DESCRIPTION_LENGTH = 1024;

  var FORM_HTML = '' +
     '<div class="container-fluid" style="word-wrap:break-word;">' +
        '<div class="row">' +
          '<div class="form-group" style="position: static;">' +
            '<label><strong>Container Name<font color="red">  *  </font></strong></label>' +
            '<input type="text" class="form-control" id="' + NAME_FIELD_ID + '" required>' +
          '</div>' +
          '<div class="form-group" style="position: static;">' +
            '<label><strong>Container Description</strong></label>' +
            '<textarea class="form-control" id="' + DESCRIPTION_FIELD_ID + '"> </textarea>' +
          '</div>' +
        '</div>' +
        '<br> <div id="' + ERROR_SECTION_ID + '" style="display: none;" class="alert alert-danger fade in">' + '</div>' +
      '</div>';

  function onModalOpen(nextButtonId){
    $("#" + ERROR_SECTION_ID).hide();
    $("#" + nextButtonId).attr("disabled", true);
    $("#" + NAME_FIELD_ID + ", #" + DESCRIPTION_FIELD_ID).on("input", function(){
      setNextButtonStatusAndErrorFieldBasedOnNameAndDescription(nextButtonId)});
  };

  function setNextButtonStatusAndErrorFieldBasedOnNameAndDescription(nextButtonId){
  var formError = getFormError();
    if (formError){
      reportError(formError);
      $("#" + nextButtonId).attr("disabled", true);
      return;
    }

    $("#" + ERROR_SECTION_ID).fadeOut()
    var name = getName();
    if (name){
      $("#" + nextButtonId).attr("disabled", false);
    } else {
      $("#" + nextButtonId).attr("disabled", true);
    }
  };

  function getName(){
    var name = $("#" + NAME_FIELD_ID).val();
    return trim.trimValueIfPossible(name);
  };

  function getDescription(){
    var description = $("#" + DESCRIPTION_FIELD_ID).val();
    return trim.trimValueIfPossible(description);
  };

  function reportError(error){
    $("#" + ERROR_SECTION_ID).text(error);
    $("#" + ERROR_SECTION_ID).fadeIn();
  };

  function getFormError(){
    var name = getName();
    var description = getDescription();

    if (name && name.length > MAX_NAME_LENGTH){
      return "The max name length is " + MAX_NAME_LENGTH +
        ". " + name + " is too long.";
    }

    if (description && description.length > MAX_DESCRIPTION_LENGTH){
      return "You may not have a description longer than " +
        MAX_DESCRIPTION_LENGTH + " characters.";
    }
  };

return {ID: ID, FORM_HTML: FORM_HTML, TAB_TITLE: TAB_TITLE, onModalOpen: onModalOpen,
  getName: getName, getDescription:getDescription};
});
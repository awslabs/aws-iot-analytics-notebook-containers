define([
  "./api",
  "./trim",
], function(api, trim){
  var ID = "step1";
  var TAB_TITLE = "1. Name";

  var ERROR_SECTION_ID = "step1_error_section";
  var INSTALL_SECTION_ID = "step1_install_section";
  var NAME_FIELD_ID = "step1_container_name";
  var DESCRIPTION_FIELD_ID = "step1_container_description_field";

  var MAX_NAME_LENGTH = 128;
  var MAX_DESCRIPTION_LENGTH = 1024;

  var UPDATE_DOCUMENTATION_LINK = "http://docs.aws.amazon.com/iotanalytics/latest/userguide/automate.html#aws-iot-analytics-update-notebook-containerization-ext";

  var INSTALL_SECTION_HTML = 'There is an update available for ' +
    'this containerization extension. The update process is documented ' +
    '<a class="alert-link" href="' + UPDATE_DOCUMENTATION_LINK +' ">here</a>.';

  var FORM_HTML = '' +
     '<div class="container-fluid" style="word-wrap:break-word;">' +
        '<div id="' + INSTALL_SECTION_ID + '" class="alert alert-info fade in" style="display: none;">' + 
           INSTALL_SECTION_HTML +
        '</div>' +
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
    revealInstallButtonIfPluginNotUpToDate();
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

    if (name !== undefined && /\s/.test(name)){
      return "The name cannot contain spaces.";
    }

    if (!name){
      return "You must specify a name.";
    }

    if (name.length > MAX_NAME_LENGTH){
      return "The max name length is " + MAX_NAME_LENGTH +
        ". " + name + " is too long.";
    }


    if (/^[-_]+[\w-]*$/.test(name)){
      return "The name cannot start with an underscore or dash.";
    }

    if (! /^[a-zA-Z0-9]+[\w-]*$/.test(name)){
      return "The name must be valid ASCII. It may only contain letters, numbers, underscores, and dashes.";
    }

    if (description && description.length > MAX_DESCRIPTION_LENGTH){
      return "You may not have a description longer than " +
        MAX_DESCRIPTION_LENGTH + " characters.";
    }
  };

  function revealInstallButtonIfPluginNotUpToDate(){
    $.when(api.getExtensionIsLatestVersion()).then(
      function(isLatestVersion){
        if (!isLatestVersion){
          revealInstallSection();
        }
      });
  };

  function revealInstallSection(){
    $("#" + INSTALL_SECTION_ID).fadeIn();
  };
  
return {ID: ID, FORM_HTML: FORM_HTML, TAB_TITLE: TAB_TITLE, onModalOpen: onModalOpen,
  getName: getName, getDescription:getDescription};
});
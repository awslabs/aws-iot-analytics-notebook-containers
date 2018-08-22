define([
  "./api",
  "./progressBar"
], function(api, progressBar){
  var ID = "step5";
  var TAB_TITLE = "5. Monitor Progress";

  // If the user exits the modal and this value is true, the wizard
  // displays a message explaining that containerization will continue in
  // the background.
  var ongoingContainerization = false;
  // The wizard exit button id is set when containerization begins. 
  // It is kept disabled until containerization has either finished or failed.
  var exitButton = "";
  
  var IOT_ANALYTICS_DATASETS_PAGE = "https://console.aws.amazon.com/iotanalytics/home#/datasets";
  var COMPLETION_SYMBOL = "✅";

  var ERROR_SECTION_ID = "step5_error_section"; 
  var IMAGE_CREATION_BAR_DIV_ID = "step5_image_creation_bar_div";
  var IMAGE_UPLOAD_BAR_DIV_ID = "step5_image_upload_bar_div";
  var IMAGE_CREATION_COMPLETE_SECTION_ID = "step5_image_creation_complete";
  var IMAGE_UPLOAD_COMPLETE_SECTION_ID = "step5_image_upload_complete";
  var IMAGE_CREATION_BAR_ID = "image_creation_bar";
  var SUCCESS_SECTION_ID = "step5_success_section";
  var IMAGE_CREATION_SECTION_ID = "step5_image_creation_section";
  var IMAGE_UPLOAD_SECTION_ID = "step5_image_upload_section";
  var IMAGE_UPLOAD_BAR_ID = "step5_image_upload_bar";

  var IMAGE_CREATION_STEP = "image_creation";
  var IMAGE_UPLOAD_STEP = "image_upload";

  var SOCKET_CLOSED_ERROR_MSG = "Our connection to the containerization process has been closed unexpectedly."
  var UPLOAD_TO_REPO_ERROR_MSG = "The containerization process has failed."
  var SUCCESS_MSG = "You can now use this notebook for scheduled analysis of your Data Sets.";

  // 15 seconds
  var SOCKET_CLOSE_REPORT_ERROR_DELAY = 15000;

  var FORM_HTML =  '' +
    '<div> ' + 
      '<div id="' + IMAGE_CREATION_SECTION_ID + '">' +
        'Creating Image... ' + '<span id="' + IMAGE_CREATION_COMPLETE_SECTION_ID + '"">' + COMPLETION_SYMBOL + '</span>' +
        progressBar.getHtml(IMAGE_CREATION_BAR_DIV_ID, IMAGE_CREATION_BAR_ID) +
      '</div>' +
      '<br>' + 
      '<div id="' + IMAGE_UPLOAD_SECTION_ID + '" class="fade in">' +
        'Uploading Image... ' + '<span id="' + IMAGE_UPLOAD_COMPLETE_SECTION_ID + '">' + COMPLETION_SYMBOL + '</span>' +
        progressBar.getHtml(IMAGE_UPLOAD_BAR_DIV_ID, IMAGE_UPLOAD_BAR_ID) +
      '</div>' +
      '<br>' + 
      '<div id="' + SUCCESS_SECTION_ID + '" class="fade in"> ' +
        SUCCESS_MSG + ' ' + 
        '<a class="btn btn-primary next" href="' + IOT_ANALYTICS_DATASETS_PAGE + '">Go To Data Sets</a> ' +
      '</div>' +
        '<div id="' + ERROR_SECTION_ID + '" class="alert alert-danger fade in">' +
        '</div>' + 
      '</div>' +
    '</div>';

  function executeContainerization(_exitButton, containerName, containerDescription, repository, variables){
    ongoingContainerization = true;
    exitButton = _exitButton;
    // indicate that we don't want them to leave until the process is complete
    // we are not actually trapping them because the modal exit button still works
    $("#" + exitButton).attr("disabled", true);

    api.uploadToRepo(repository, variables, containerName, containerDescription,
      handleResponse, handleUploadToRepoError, handleSocketClose);
    $("#" + IMAGE_CREATION_SECTION_ID).fadeIn();
  };

  function handleResponse(step, progress, errorMsg){
    if (errorMsg){
      handleError(errorMsg);
      return;
    };
    if (step === IMAGE_CREATION_STEP){
      handleImageCreation(progress);
      return;
    }
    if (step === IMAGE_UPLOAD_STEP){
      handleImageUpload(progress);
      return;
    }
  };

  function handleError(errorMsg){
    handleContainerizationNoLongerRunning();
    $("#" + ERROR_SECTION_ID).text(errorMsg);
    $("#" + ERROR_SECTION_ID).fadeIn();
    $("#" + IMAGE_CREATION_BAR_DIV_ID).fadeOut();
    $("#" + IMAGE_UPLOAD_BAR_DIV_ID).fadeOut();
  };

  function handleImageCreation(progress){
    progressBar.update(IMAGE_CREATION_BAR_ID, IMAGE_CREATION_BAR_DIV_ID, progress);
    if (progress === 100){
      $("#" + IMAGE_CREATION_BAR_DIV_ID).fadeOut();
      $("#" + IMAGE_CREATION_COMPLETE_SECTION_ID).show();
      $("#" + IMAGE_UPLOAD_SECTION_ID).fadeIn();
    }
  };

   function handleImageUpload(progress){
    progressBar.update(IMAGE_UPLOAD_BAR_ID, IMAGE_UPLOAD_BAR_DIV_ID, progress);
    if (progress === 100){
      handleContainerizationNoLongerRunning();
      $("#" + IMAGE_UPLOAD_BAR_DIV_ID).fadeOut();
      $("#" + IMAGE_UPLOAD_COMPLETE_SECTION_ID).fadeIn();
      $("#" + SUCCESS_SECTION_ID).fadeIn();
    }
  };

  function handleContainerizationNoLongerRunning(){
    ongoingContainerization = false;
    if (exitButton){
      $("#" + exitButton).attr("disabled", false);
    }
  };

  function handleUploadToRepoError(){
    handleError(UPLOAD_TO_REPO_ERROR_MSG);
  };

  function handleSocketClose(){
    // if the socket is closed before containerization is complete
    // then report an error
    setTimeout(function (){
      if (containerizationIsOngoing()){
        handleError(SOCKET_CLOSED_ERROR_MSG);
      }
    // give messages bearing news of containerization success
    // some more time to come in before admitting defeat
    }, SOCKET_CLOSE_REPORT_ERROR_DELAY);
  };

  function onModalOpen(){
    $("#" + IMAGE_CREATION_SECTION_ID).hide();
    $("#" + IMAGE_UPLOAD_SECTION_ID).hide();
    $("#" + ERROR_SECTION_ID).hide();
    $("#" + IMAGE_UPLOAD_COMPLETE_SECTION_ID).hide();
    $("#" + IMAGE_CREATION_COMPLETE_SECTION_ID).hide();
    $("#" + SUCCESS_SECTION_ID).hide();
  };

  function containerizationIsOngoing(){
    return ongoingContainerization;
  };

return {ID: ID, FORM_HTML: FORM_HTML, TAB_TITLE: TAB_TITLE, onModalOpen:onModalOpen,
  executeContainerization: executeContainerization,
  containerizationIsOngoing: containerizationIsOngoing};
});
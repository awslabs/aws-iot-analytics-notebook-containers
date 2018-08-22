define([
  "base/js/dialog",
  "./step1Name",
  "./step2Variables",
  "./step3Repository",
  "./step4Review",
  "./step5Monitor",
  "./api",
  "./external/datatables.min",
], function(dialog, step1, step2, step3, step4, step5, api){
  var MODAL_TITLE = "Containerize Notebook";

  var EXIT_BUTTON_ID = "exit_wizard_button";
  var STEP1_NEXT_BUTTON_ID = "step1_next";
  var STEP2_NEXT_BUTTON_ID = "step2_next";
  var STEP3_NEXT_BUTTON_ID = "step3_next";
  var STEP4_NEXT_BUTTON_ID = "step4_next";
  var STEP1_PREVIOUS_BUTTON_ID = "step1_previous";
  var STEP2_PREVIOUS_BUTTON_ID = "step2_previous";
  var STEP3_PREVIOUS_BUTTON_ID = "step3_previous";
  var STEP4_PREVIOUS_BUTTON_ID = "step4_previous";
  var NEXT_BUTTON_COL_WHEN_PREV_ABSENT = 12;
  var NEXT_BUTTON_COL_WHEN_PREV_PRESENT = 6;

  var WIZARD_NEXT_CLASS = "wizard-next";
  var WIZARD_PREVIOUS_CLASS = "wizard-previous";
  var WIZARD_TAB_CLASS = "wizard-tab";

  var BACKEND_ERROR_MODAL_TITLE = "Containerization Error";
  var BACKEND_ERROR_MSG = "We encountered an unexpected error when checking for ongoing " +
    "containerization attempts. If this error persists, please contact AWS " +
    "Technical Support. If you installed the containerization extension manually, please " +
    "verify that the installation was successful.";
  var BACKGROUND_PROCESSING_MODAL_TITLE = "Background Processing Notice";
  var INVALID_KERNEL_MODAL_TITLE = "Invalid Kernel Notice";
  var CONTAINERIZATION_ONGOING_MODAL_TITLE = "Ongoing Containerization Notice";
  var CONTAINERIZATION_ONGOING_ERROR_MSG = "A notebook on this instance is currently being " + 
    "containerized. You may only containerize one notebook at a time per Sagemaker Instance.";

  var CONTAINERIZED_KERNEL_PREFIX = "containerized";
  var IOT_CONSOLE_NOTEBOOKS_LINK = "https://console.aws.amazon.com/iotanalytics/home#/notebooks";

  var DATATABLE_CSS_PATH = "nbextensions/iota_notebook_containers/external/datatables.min.css";

  var WIZARD_HTML = '' + 
    '<div class="navbar">' +
      '<div class="navbar-inner">' +
        '<ul class="nav nav-pills ' + WIZARD_TAB_CLASS + '">' +
          '<li class="disabled active"><a href=#' + step1.ID + ' ">' + step1.TAB_TITLE + '</a></li>' +
           '<li class="disabled"><a href=#' + step2.ID + ' ">' + step2.TAB_TITLE + '</a></li>' +
           '<li class="disabled"><a href=#' + step3.ID + ' ">' + step3.TAB_TITLE + '</a></li>' +
           '<li class="disabled"><a href=#' + step4.ID + ' ">' + step4.TAB_TITLE + '</a></li>' +
           '<li class="disabled"><a href=#' + step5.ID + ' ">' + step5.TAB_TITLE + '</a></li>' +
        '</ul>' +
      '</div>' +
  '</div>' +
  '<div class="tab-content container-fluid">' +
      '<div class="tab-pane fade in active" id="' + step1.ID + '">' +
        '<div class="well">' +
          step1.FORM_HTML +
        '</div>' +
        '<div class="row">' +
          getNextButtonDivHtml(STEP1_NEXT_BUTTON_ID,
            NEXT_BUTTON_COL_WHEN_PREV_ABSENT) +
        '</div>' +
      '</div>' +
      '<div class="tab-pane fade" id="' + step2.ID + '">' +
        '<div class="well">' +
          step2.FORM_HTML +
        '</div>' +
        '<div class="row">' +
          getPreviousButtonDivHtml(STEP2_PREVIOUS_BUTTON_ID) +
          getNextButtonDivHtml(STEP2_NEXT_BUTTON_ID,
            NEXT_BUTTON_COL_WHEN_PREV_PRESENT) +
        '</div>'  +
      '</div>' +
    '<div class="tab-pane fade" id="' + step3.ID + '">' +
      '<div class="well">' +
          step3.FORM_HTML +
      '</div>' +
      '<div class="row">' +
        getPreviousButtonDivHtml(STEP3_PREVIOUS_BUTTON_ID) +
        getNextButtonDivHtml(STEP3_NEXT_BUTTON_ID,
          NEXT_BUTTON_COL_WHEN_PREV_PRESENT) +
      '</div> ' +
    '</div>' +
    '<div class="tab-pane fade" id="' + step4.ID + '">' +
      '<div class="well">' +
        step4.FORM_HTML +
      '</div>' +
      '<div class="row">' +
        getPreviousButtonDivHtml(STEP4_PREVIOUS_BUTTON_ID) +
        '<div class="pull-right text-right">' +
          '<a class="btn btn-primary ' + WIZARD_NEXT_CLASS + '" id="' +
            STEP4_NEXT_BUTTON_ID + '" href="#">Containerize</a>' +
        '</div> ' +
      '</div>' +
    '</div>' +
    '<div class="tab-pane fade" id="' + step5.ID + '">' +
      '<div class="well"> ' +
        step5.FORM_HTML +
      '</div>' +
    '</div>' +
  '</div>';

  function launchModal(keyboard_manager){  
    var kernel = Jupyter.notebook.kernel["name"];
    // if the kernel doesn't begin with "containerized" we cannot containerize the notebook
    if (kernel.lastIndexOf(CONTAINERIZED_KERNEL_PREFIX, 0) !== 0){
      launchInvalidKernelModal(keyboard_manager, kernel);
      return;
    }

    $.when(api.isContainerizationOngoing()).then(function(containerization_ongoing){
      if (containerization_ongoing){
        launchContainerizationOngoingModal(keyboard_manager);
      } else {
          var modal = launchFiveStepModal(keyboard_manager);
          modal.on("hidden.bs.modal", function (){
            if (step5.containerizationIsOngoing()){
              launchBackgroundProcessingModal(keyboard_manager);
            }
          });   
        }  
    }, function(){
        launchBackendErrorModal(keyboard_manager);
    });
  };

  function launchFiveStepModal(keyboard_manager){
    return dialog.modal({
      title: MODAL_TITLE,
      body: $(WIZARD_HTML),
      open: onModalOpen,
      keyboard_manager: keyboard_manager,
      buttons: {
        Exit: {id: EXIT_BUTTON_ID},
      }
    });
  };

  function launchBackgroundProcessingModal(keyboard_manager){
    return dialog.modal({
      title: BACKGROUND_PROCESSING_MODAL_TITLE,
      body: $(getBackgroundProcessingNoticeHtml()),
      keyboard_manager: keyboard_manager,
      buttons: {
        OK: {},
      }
    });
  };

  function launchInvalidKernelModal(keyboard_manager, kernel){
    return dialog.modal({
      title: INVALID_KERNEL_MODAL_TITLE,
      body: getInvalidKernelMessage(kernel),
      keyboard_manager: keyboard_manager,
      buttons: {
        OK: {},
      }
    });
  };

  function launchContainerizationOngoingModal(keyboard_manager){
    return dialog.modal({
      title: CONTAINERIZATION_ONGOING_MODAL_TITLE,
      body: CONTAINERIZATION_ONGOING_ERROR_MSG,
      keyboard_manager: keyboard_manager,
      buttons: {
        OK: {},
      }
    });
  };

  function launchBackendErrorModal(keyboard_manager){
    return dialog.modal({
      title: BACKEND_ERROR_MODAL_TITLE,
      body: BACKEND_ERROR_MSG,
      keyboard_manager: keyboard_manager,
      buttons: {
        OK: {},
      }
    });
  };

  function onModalOpen(){
    loadDataTableCss();
    step1.onModalOpen(STEP1_NEXT_BUTTON_ID);
    step2.onModalOpen();
    step3.onModalOpen(STEP3_NEXT_BUTTON_ID);
    step4.onModalOpen();
    step5.onModalOpen();

    // prevent clicking the tabs from doing anything
    // we just want them to display the current step, not navigate
    $("." + WIZARD_TAB_CLASS).on("click", function(event){
      event.preventDefault();
    });

    $("." + WIZARD_PREVIOUS_CLASS).click(function(){
      loadPreviousTab(this);
      return false;  
      });

    $("#" + STEP1_NEXT_BUTTON_ID).on("click", function(){
      loadNextIfButtonNotDisabled(this, STEP1_NEXT_BUTTON_ID);
      return false;   
    });

    $("#" + STEP2_NEXT_BUTTON_ID).on("click", function(){
      if (!step2.reportErrorsIfNotValid()){
        loadNextTab(this);
      }
      return false;   
    });

    $("#" + STEP3_NEXT_BUTTON_ID).on("click", function(){
      step4.updateReviewContent(step1.getName(), step1.getDescription(),
        step3.getRepository(), step2.getVariables());
      loadNextIfButtonNotDisabled(this, STEP3_NEXT_BUTTON_ID);
      return false;   
    });

    $("#" + STEP4_NEXT_BUTTON_ID).on("click", function(){
      step5.executeContainerization(EXIT_BUTTON_ID, step1.getName(),
        step1.getDescription(), step3.getRepository(), step2.getVariables());
      loadNextTab(this);
      return false;   
    });
  };

  function getInvalidKernelMessage(kernel){
    return 'This feature may only be used on notebooks ' +
    'running a containerized kernel. Such kernels have the word "Containerized" ' +
    'at the beginning of their names. You may not use containerization right now because ' +
    'this notebook is being run with the "' + kernel + '" kernel.';
  };

  function getBackgroundProcessingNoticeHtml(){
    return '<div> We will continue containerizing your notebook in the background. ' +
    'You may monitor the containerization status in the ' +
    '<a href="' + IOT_CONSOLE_NOTEBOOKS_LINK + '">AWS Iot Analytics Console</a>.</div>';
  };

  function getNextButtonDivHtml(nextButtonId, col){
    return ' ' +
    '<div class="pull-right text-right">' +
      '<a class="btn btn-default ' + WIZARD_NEXT_CLASS + '" id="' +
        nextButtonId + '" href="#">Next</a>' +
    '</div> ';
  };

  function getPreviousButtonDivHtml(previousButtonId){
    return ' ' +
    '<div class="pull-left text-left">' +
      '<a class="btn btn-default ' + WIZARD_PREVIOUS_CLASS + '" id="' +
        previousButtonId + '" href="#">Previous</a>' +
    '</div> ';
  };

  function loadNextTab(clicked){
    var nextId = $(clicked).parents(".tab-pane").next().attr("id");
    $("a[href='#"+nextId+"']").tab("show"); 
  };

  function loadPreviousTab(clicked){
    var previousId = $(clicked).parents(".tab-pane").prev().attr("id");
    $("a[href='#" + previousId+"']").tab("show");
  };

  function loadNextIfButtonNotDisabled(clicked, buttonId){
    if (! $("#" + buttonId).attr("disabled")){
      loadNextTab(clicked);
    }
  };

  function loadDataTableCss(){
    var url = require.toUrl(DATATABLE_CSS_PATH);
    $("head").append('<link type="text/css" rel="stylesheet" href=' + url + '>');
  };

  return {launchModal: launchModal};
})
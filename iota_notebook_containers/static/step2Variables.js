define([
  "./api",
  "./variable",
  "./trim",
], function(api, variableModule, trim){
  var ID = "step2";
  var TAB_TITLE = "2. Input Variables";

  var ADD_DETECTED_VAR_BUTTON_ID = "step2_add_var_button";
  var ADD_CUSTOM_VAR_BUTTON_ID = "step2_add_custom_var_button";
  var ERROR_SECTION_ID = "step2_error_section"; 
  var EXECUTE_NOTEBOOK_MSG_SECTION_ID = "step2_execute_notebook_msg_section"; 
  var TABLE_ID = "step2_variable_list";

  var DELETE_BUTTON_CLASS = "step2_delete_button";

  var VARIABLE_DESCRIPTION_CLASS = "step2_variable_description";
  var VARIABLE_NAME_CLASS = "step2_variable_name";
  var VARIABLE_TYPE_CLASS = "step2_variable_type";

  var CONTAINER_NAME_VAR = "@iota_container_name";
  var CONTAINER_DESC_VAR = "@iota_container_description";
  var MAX_NUM_VARIABLES = 50;
  var MAX_VARIABLE_NAME_LENGTH = 256;
  var MAX_VARIABLE_DESCRIPTION_LENGTH = 1024;

  var DATATABLE_PAGE_LENGTH = 5;
  var DATATABLE_COLUMN_DEFS = {className: "dt-center", targets: "_all"};
  var DATATABLE_LANGUAGE = {
    "lengthMenu": "Display _MENU_ variables per page",
    "zeroRecords": "No variables specified.",
    "info": "Showing _START_ to _END_ of _TOTAL_ variables",
    "infoEmpty": "",
    "infoFiltered": "(filtered from _MAX_ total variables)"
  };
  var DATATABLE_OPTIONS = "rtip";
  var DATATABLE_ORDERING_ENABLED = false;

  var DELETE_SYMBOL = "❌";

  var EXECUTE_NOTEBOOK_TO_AUTODETECT_VARS_MSG = "Run your notebook to auto-populate this table.";

  var CUSTOM_VAR_TOOLTIP = 'Variables are an optional way to pass input to your notebook at run-time.';
  var CUSTOM_VAR_TOOLTIP_HTML = 'data-toggle="tooltip" data-placement="top" title="' +
    CUSTOM_VAR_TOOLTIP + '"';
  var CUSTOM_NAME_FORM = '<input type="text" class="form-control ' +
    VARIABLE_NAME_CLASS +'">';
  var DELETE_FORM = '<a href="#" class="btn ' + DELETE_BUTTON_CLASS
    + ' "> ' + DELETE_SYMBOL + '</a>';
  var DESCRIPTION_FORM = '<input type="text" class="form-control '
    + VARIABLE_DESCRIPTION_CLASS +'">';
  var DETECTED_NAME_FORM_NO_OPTIONS = '' +
    '<select class="form-control ' + VARIABLE_NAME_CLASS + '">' +
    '</select>';
  var TYPE_FORM = '' + 
    '<select class="form-control ' + VARIABLE_TYPE_CLASS + '">' +
      '<option value="" selected disabled>Select A Type</option>' +
      '<option value="string">String</option>' +
      '<option value="double">Double</option>' +
      '<option value="outputFileUri">OutputFileUri</option>' +
      '<option value="datasetContentVersionId">DatasetContentVersionId</option>' +
    '</select>';
  var FORM_HTML = '<div style="word-wrap:break-word;">' +
  '<div id="' + EXECUTE_NOTEBOOK_MSG_SECTION_ID + '" class="alert alert-info fade in" style="display: none;">' + 
    EXECUTE_NOTEBOOK_TO_AUTODETECT_VARS_MSG +
  '</div>' +
   '<div class="container-fluid" style="display:grid;">' +
      '<table id="' + TABLE_ID + '" class="row-border" style="width:100%">' +
        '<thead>' +
          '<tr>' +
            '<th>Name</th>' +
            '<th>Type</th>' +
            '<th>Description</th>' +
            '<th></th>' +
          '</tr>' +
        '</thead>' +
        '<tbody id="body"></tbody>' +
      '</table>' +
   '</div>' +
   '<div class="row btn-toolbar" align="left">' +
    '<a class="btn btn-default" href="#" ' + CUSTOM_VAR_TOOLTIP_HTML + ' id="' +
      ADD_CUSTOM_VAR_BUTTON_ID +'">Add Variable</a>' +
   '</div>' + 
    '<br> <div id="' + ERROR_SECTION_ID + '" class="alert alert-danger fade in" style="display: none;"></div>' +
  '</div>';

  function onModalOpen(){
    api.listVariables(addDetectedVariableRowsOrShowMessage);
    $("#" + ERROR_SECTION_ID).hide();
    $("#" + EXECUTE_NOTEBOOK_MSG_SECTION_ID).hide();
    createTable();
    $("#" + TABLE_ID).off('click').on("click", "." + DELETE_BUTTON_CLASS, deleteRowOnClick);
    $("#" + ADD_CUSTOM_VAR_BUTTON_ID).on("click", addCustomVariableRow);
  };

  function getTable(){
    return $("#" + TABLE_ID).DataTable();
  };

  function createTable(){
    this.paramDataTable = $("#" + TABLE_ID).DataTable({
      ordering: DATATABLE_ORDERING_ENABLED,
      columnDefs: [DATATABLE_COLUMN_DEFS],
      pageLength: DATATABLE_PAGE_LENGTH,
      language: DATATABLE_LANGUAGE,
      dom: DATATABLE_OPTIONS,
    });
  };

  function getVariables(){
    var dt = getTable();
    var types = getTypes();
    var names = getNames();
    var descriptions = getDescriptions();

    var variables = [];
    for(i=0, len=types.length; i < len; i++){
      variables.push(new variableModule.Variable(names[i], types[i], descriptions[i]));
    };
    return variables;
  };

  function getDescriptions(){
    var descriptions = [];
    var dt = getTable();
    var descriptionInputs = dt.$("." + VARIABLE_DESCRIPTION_CLASS);
    for(i=0, len=descriptionInputs.length; i<len; i++){
      var descriptionInput = descriptionInputs[i];
      var description = $(descriptionInput).val();
      descriptions.push(trim.trimValueIfPossible(description));
    }
    return descriptions;
  };

  function getTypes(){
    var types = [];
    var dt = getTable();
    var typeSelections = dt.$('.' + VARIABLE_TYPE_CLASS + ' :selected');
    for(i=0, len=typeSelections.length; i<len; i++){
      var selectedType = typeSelections[i];
      types.push($(selectedType).val());
    }
    return types;
  };  

  function getNames(){
    var names = [];
    var dt = getTable();
    var nameForms = dt.$("." + VARIABLE_NAME_CLASS);
    for(i=0, len=nameForms.length; i<len; i++){
      var nameForm = nameForms.eq(i);
      var name = $(nameForm).val();
      names.push(trim.trimValueIfPossible(name));
    }
    return names;
  };  

  function getFormError(){
    var names = getNames();
    var types = getTypes();
    var descriptions = getDescriptions();

    if (names === null && type === null && descriptions === null){
      return false;
    }
    if (name === null){
      if (types !== null || descriptions !== null){
        return "You must specify a name for every variable.";
      };
    }
    if (types === null){
      if (names !== null || descriptions !== null){
        return "You must specify a type for every variable.";
      };
    }
    if (names.length != types.length){
      return "You must specify a name and type for every variable.";
    }
    if (descriptions !== null && names.length !== descriptions.length){
      return "You must specify a name for every variable.";
    }

    for(i=0, len=names.length; i<len; i++){
      var name = names[i];
      if (! name){
        return "You must specify a name for every variable.";
      }
      if (name === CONTAINER_NAME_VAR || name === CONTAINER_DESC_VAR){
        return name + " is reserved. You may not use that variable name.";
      }
      if (name.length > MAX_VARIABLE_NAME_LENGTH){
        return "The max variable name length is " + MAX_VARIABLE_NAME_LENGTH +
          ". " + name + " is too long.";
      }
      for(j=0, len=names.length; j<len; j++){
        if (i !== j && names[j] === name){
          return name + " is listed multiple times. Each variable must have a unique name.";
        }
      }
    }

    for(i=0, len=types.length; i<len; i++){
      var type = types[i];
      if (! type || type === "Select A Type"){
        return "You must specify a type for every variable.";
      }
    }

    for(i=0, len=descriptions.length; i<len; i++){
      var description = descriptions[i];
      if (description && description.length > MAX_VARIABLE_DESCRIPTION_LENGTH){
        return "You may not have a description longer than " +
          MAX_VARIABLE_DESCRIPTION_LENGTH + " characters.";
      }
    }
    return false;
  };

  function reportError(error){
      $("#" + ERROR_SECTION_ID).text(error);
      $("#" + ERROR_SECTION_ID).fadeIn();
    };

  function reportErrorsIfNotValid(){
    var formError = getFormError();
    if (formError){
      reportError(formError);
      return true;
    } else{
     $("#" + ERROR_SECTION_ID).fadeOut();
     return false; 
    }
  };
  
  function addDetectedVariableRowsOrShowMessage(variables){
    if (Array.isArray(variables) && variables.length){
      for(i=0, len=Math.min(variables.length, MAX_NUM_VARIABLES); i<len; i++){
        var variable = variableModule.buildFromDetectedVariable(variables[i]);
        addDetectedVariableRow(variable.name, variable.type);
      }
    } else {
      $("#" + EXECUTE_NOTEBOOK_MSG_SECTION_ID).fadeIn();
    }
  };

  function addDetectedVariableRow(variableName, variableType){
    var nameForm = '<input value="' + variableName +
      '" type="text" class="form-control ' +
      VARIABLE_NAME_CLASS + '" readonly>';
    var dt = $("#" + TABLE_ID).DataTable();
    dt.row.add([nameForm, TYPE_FORM, DESCRIPTION_FORM, DELETE_FORM]);

    var row = $(dt.row(':last').node());
    row.find("." + VARIABLE_TYPE_CLASS).val(variableType);

    dt.order([1, 'asc']).draw();
  };

  function addCustomVariableRow(){
    var dt = $("#" + TABLE_ID).DataTable();
    if (dt.rows().count() < MAX_NUM_VARIABLES){
      dt.row.add([CUSTOM_NAME_FORM, TYPE_FORM, DESCRIPTION_FORM, DELETE_FORM]);
      dt.order([1, 'asc']).draw();
      dt.page('last').draw(false);
    } else {
      reportError("You may only define " + MAX_NUM_VARIABLES + " variables.");
    }
  };

  function deleteRowOnClick(){
    var dt = getTable();
    dt.row($(this).closest('tr')).remove().draw(false);
  };

return {ID: ID, FORM_HTML: FORM_HTML, TAB_TITLE: TAB_TITLE, onModalOpen: onModalOpen, getVariables: getVariables, reportErrorsIfNotValid:reportErrorsIfNotValid};
});
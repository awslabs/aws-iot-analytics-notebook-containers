define([
], function(){
  var ID = "step4";
  var TAB_TITLE = "4. Review";

  var CONTAINER_NAME_ID = "step4_container_name";
  var CONTAINER_DESCRIPTION_ID = "step4_container_description";
  var REPOSITORY_ID = "step4_destination_repo";
  var VARIABLE_TABLE_ID = "step4_variable_table";

  var DATATABLE_COLUMN_DEFS = [{className: "dt-center", "targets": "_all"}];
  var FORM_HTML = '<div style="overflow: auto;"> ' +
    '<div><strong> Container Name: </strong> <span id="' + CONTAINER_NAME_ID + '"> </span></div>' +
    '<div><strong> Container Description: </strong> <span id="' + CONTAINER_DESCRIPTION_ID + '"></span></div>' +
    '<div><strong> Upload To: </strong> <span id="' + REPOSITORY_ID + '"></span></div> <br>' +
    '<div>' + 
      '<table + class="table table-striped table-bordered" style="width:100%;" id="' + VARIABLE_TABLE_ID + '">' +
        '<thead>' +
          '<tr>' +
            '<th>Variable Name</th>' +
            '<th>Type</th>' +
            '<th>Description</th>' +
          '</tr>' +
        '</thead>' +
        '<tbody>' +
        '</tbody>' +
      '</table>' + 
    '</div>' +
  '</div>';

  var DATATABLE_PAGE_LENGTH = 5;
  var DATATABLE_LANGUAGE = {
    "lengthMenu": "Display _MENU_ variables per page",
    "zeroRecords": "No variables specified.",
    "info": "Showing _START_ to _END_ of _TOTAL_ variables",
    "infoEmpty": "",
    "infoFiltered": "(filtered from _MAX_ total variables)"
  };
  var DATATABLE_OPTIONS = "rtip";
  var DATATABLE_ORDERING_ENABLED = false;
 
  function onModalOpen(){
    createTable();
  };

  function createTable(){
    $("#" + VARIABLE_TABLE_ID).DataTable({
      columnDefs: DATATABLE_COLUMN_DEFS,
      pageLength: DATATABLE_PAGE_LENGTH,
      language: DATATABLE_LANGUAGE,
      dom: DATATABLE_OPTIONS,
      ordering: DATATABLE_ORDERING_ENABLED
    });
  };

  function updateReviewContent(name, description, repository, variables){
    $("#" + CONTAINER_NAME_ID).text(name);
    $("#" + CONTAINER_DESCRIPTION_ID).text(description);
    $("#" + REPOSITORY_ID).text(repository);

    var dt = getTable();
    dt.clear();

    for(i=0, len=variables.length; i < len; i++){
      var variable = variables[i];
      dt.row.add([variable.name, capitalizeFirstLetter(variable.type), variable.description]).draw(false);
    }
  };

  function getTable(){
    return $("#" + VARIABLE_TABLE_ID).DataTable();
  };

  function capitalizeFirstLetter(word){
    if (word && word.length > 0){
      return word.charAt(0).toUpperCase() + word.slice(1);
    } else {
      return word;
    }
  };

return {ID: ID, FORM_HTML: FORM_HTML, TAB_TITLE: TAB_TITLE, onModalOpen: onModalOpen,
  updateReviewContent: updateReviewContent};
});
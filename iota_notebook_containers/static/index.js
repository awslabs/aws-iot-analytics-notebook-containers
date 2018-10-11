define([
    "base/js/namespace",
    "jquery",
    "./wizard"
], function(Jupyter, $, wizard){

  var NOTEBOOK_INIT_EVENT = "app_initialized.NotebookApp";

  function addContainerizeToToolbar(){
    if (!Jupyter.toolbar){
      $([Jupyter.events]).on(NOTEBOOK_INIT_EVENT, addContainerizeToToolbar);
      return;
    }
    Jupyter.toolbar.add_buttons_group([
      {
       'id'      : "containerize_button",
       'label'   : "Containerize",
       'icon'    : "fa-cube",
       'callback': function(){
          Jupyter.notebook.save_notebook();
          wizard.launchModal(Jupyter.keyboard_manager);
        }
      }
    ]);
  };

  return {
    load_ipython_extension: addContainerizeToToolbar
  };
});
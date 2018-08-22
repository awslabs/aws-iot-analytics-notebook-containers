define([
], function(){
  function Variable(name, type, description) {
    this.name = name;
    this.type = type;
    this.description = description;
  };

  function buildFromDetectedVariable(detectedVariable){
    var name = detectedVariable["varName"];
    var type = detectedVariable["varType"];
    var description = "";
    return new Variable(name, type, description);
};

return {Variable: Variable, buildFromDetectedVariable: buildFromDetectedVariable};
});
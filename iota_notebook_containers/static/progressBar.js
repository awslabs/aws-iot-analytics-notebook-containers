define([
], function(){
  var ANIMATION_SPEED = "fast";
  var VAL_FIELD = "val";

  function getHtml(barDivId, barId){
    return '' + 
    '<div class="progress" id="' + barDivId + '">' +
      '<div class="progress-bar" id="' + barId + '" ' + VAL_FIELD + ' =1 style="width: 0px;min-width:0px;" role="progressbar"> </div>' +
    '</div>'
  };

  function update(barId, barDivId, newValue){
    var bar = $("#" + barId);
    var oldValue = parseInt(bar.attr(VAL_FIELD));
    if (newValue > oldValue){
      bar.attr(VAL_FIELD, newValue);
      draw(barId, barDivId, newValue);
    }
  };

  function draw(barId, barDivId, progressPercentage){
    var progressFraction = progressPercentage/100;
    var bar = $("#" + barId);
    var barDiv = $("#" + barDivId);
    var barWidth = Math.round(progressFraction * barDiv.width());
    bar.animate({width: barWidth}, ANIMATION_SPEED);
  };

  return {
      getHtml: getHtml, update: update
  };
});
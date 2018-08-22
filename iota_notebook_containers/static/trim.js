define([
], function(){
  function trimValueIfPossible(word){
    if (word){
      return word.trim();
    } else {
      return word;
    }
  };
return {trimValueIfPossible: trimValueIfPossible};
});
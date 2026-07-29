// camofox /evaluate に渡す。React制御input/select/textarea/checkbox に値設定
window.__cap = {
  setEl: function(el, v){ var p = el.tagName==='TEXTAREA'?window.HTMLTextAreaElement.prototype:(el.tagName==='SELECT'?window.HTMLSelectElement.prototype:window.HTMLInputElement.prototype); Object.getOwnPropertyDescriptor(p,'value').set.call(el, v); el.dispatchEvent(new Event('input',{bubbles:true})); el.dispatchEvent(new Event('change',{bubbles:true})); },
  setByIndex: function(i, v){ this.setEl(document.querySelectorAll('input,select,textarea')[i], v); },
  check: function(i, on){ var el=document.querySelectorAll('input[type=checkbox]')[i]; if(!!el.checked!==!!on) el.click(); }
};


async function loadLang(code){
  const res = await fetch(`/static_lang/${code}.json`);
  const dict = await res.json();
  window.NQ_I18N = dict;
  document.querySelectorAll('[data-i18n]').forEach(el=>{
    const key = el.getAttribute('data-i18n').split('.').reduce((o,k)=>o?o[k]:null, dict);
    if(typeof key==='string') el.textContent = key;
  });
}
document.addEventListener('DOMContentLoaded',()=>{
  const sel=document.getElementById('langSelect');
  if(sel){ sel.addEventListener('change',()=>{
    document.cookie = 'lang='+sel.value+';path=/;max-age='+(60*60*24*365);
    loadLang(sel.value);
  }); }
});

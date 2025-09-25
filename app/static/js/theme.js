
(function(){
  const root=document.documentElement;
  const prefers=window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';
  const saved=localStorage.getItem('theme')||'auto';
  const apply=(m)=>{root.setAttribute('data-theme', m==='auto' ? (prefers==='dark'?'dark':'light') : m)};
  apply(saved);
  document.addEventListener('DOMContentLoaded',()=>{
    const sel=document.getElementById('themeSelect'); if(!sel) return;
    sel.value=saved; sel.addEventListener('change',e=>{localStorage.setItem('theme', e.target.value); apply(e.target.value);});
  });
})();

/* TwoComma News router. Views are pre-rendered by build.py into data.json; this file only swaps them in by hash,
   handles calendar zoom (buttons, pinch, ctrl+scroll, +/-, back button) and the accessible writeup modal. */
(()=>{
let D,cur={v:'home'};const view=document.getElementById('view');
// UI strings for the page's language come from window.TCN_T (inline <head> script, built from i18n/ui.<lang>.json); English fallback.
const EN={'a11y.modal_close':'Close','modal.close_symbol':'×','item.permalink':'Permalink','empty.view':'Nothing here yet.','empty.back_to_latest':'Back to latest','title.page':'{title} | TwoComma News'};
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const T=(k,o={})=>((window.TCN_T||{})[k]||EN[k]||k).replace(/\{(\w+)\}/g,(m,n)=>n in o?o[n]:m);
const LP=document.documentElement.dataset.lp||'/news'; // '' (English) or '/zh-hant' | '/zh-hans'
const isoWeek=s=>{const d=new Date(s+'T00:00:00Z'),day=(d.getUTCDay()+6)%7;d.setUTCDate(d.getUTCDate()-day+3);const y=d.getUTCFullYear(),j=new Date(Date.UTC(y,0,4));
  return `${y}-W${String(1+Math.round(((d-j)/864e5-3+((j.getUTCDay()+6)%7))/7)).padStart(2,'0')}`};
const dayList=()=>Object.keys(D.days).sort();
function parse(){const m=location.hash.match(/^#\/(day|week|month)\/([\w-]+)$/);return m?{v:m[1],k:m[2]}:{v:'home'}}
function anchor(){const{v,k}=cur,ds=dayList();if(v=='day')return k;
  if(v=='week'){const x=ds.filter(d=>D.days[d].w==k);return x.pop()||D.latest}
  if(v=='month'){const x=ds.filter(d=>d.startsWith(k));return x.pop()||D.latest}return D.latest}
function go(l,a){if(!D.days[a])a=D.latest;location.hash=`#/${l}/${l=='day'?a:l=='week'?D.days[a].w:a.slice(0,7)}`}
function zoom(dir){const lv=['day','week','month'],i=lv.indexOf(cur.v),j=i<0?(dir>0?1:0):Math.max(0,Math.min(2,i+dir));if(j!==i)go(lv[j],anchor())}
function render(first){cur=parse();const key=cur.v=='home'?'home':cur.v+'/'+cur.k;
  view.innerHTML=D.views[key]||`<p>${esc(T('empty.view'))} <a href="#/">${esc(T('empty.back_to_latest'))}</a></p>`;
  document.querySelectorAll('[data-nav]').forEach(a=>{const on=a.dataset.nav==cur.v;a.classList.toggle('on',on);if(a.closest('.seg')||a.classList.contains('home'))on?a.setAttribute('aria-current','page'):a.removeAttribute('aria-current');
    const an=anchor();a.href=a.dataset.nav=='home'?'#/':`#/${a.dataset.nav}/${a.dataset.nav=='day'?an:a.dataset.nav=='week'?D.days[an].w:an.slice(0,7)}`});
  document.querySelectorAll('.seg [data-z="-1"]').forEach(b=>b.disabled=cur.v=='day');document.querySelectorAll('.seg [data-z="1"]').forEach(b=>b.disabled=cur.v=='month');
  document.title=T('title.page',{title:view.querySelector('h1')?.textContent||''}).replace(/\s{2,}/g,' ').trim();
  if(!first){const h=view.querySelector('h1');h&&h.focus({preventScroll:true});scrollTo(0,0)}}
document.addEventListener('click',e=>{const b=e.target.closest('.seg button[data-z]');b&&zoom(+b.dataset.z)});
view.addEventListener('click',e=>{const a=e.target.closest('a.hl');if(a&&D&&!e.metaKey&&!e.ctrlKey&&!e.shiftKey&&e.button==0){e.preventDefault();openModal(a.dataset.id,a)}});
let lock=0;addEventListener('wheel',e=>{if(!e.ctrlKey||!D||modal.classList.contains('open'))return;e.preventDefault();const t=Date.now();if(t-lock<450||Math.abs(e.deltaY)<4)return;lock=t;zoom(e.deltaY>0?1:-1)},{passive:false});
let p0=null;const dist=t=>Math.hypot(t[0].clientX-t[1].clientX,t[0].clientY-t[1].clientY);
addEventListener('touchstart',e=>{p0=e.touches.length==2?dist(e.touches):null},{passive:true});
addEventListener('touchmove',e=>{if(p0&&e.touches.length==2&&D){e.preventDefault();const r=dist(e.touches)/p0;if(r<.7||r>1.4){zoom(r<1?1:-1);p0=null}}},{passive:false});
addEventListener('touchend',()=>p0=null);
addEventListener('keydown',e=>{if(!D||modal.classList.contains('open')||e.ctrlKey||e.metaKey)return;if(e.key=='+'||e.key=='=')zoom(-1);if(e.key=='-')zoom(1)});
// Modal: Boa's .modal/.box styles; role=dialog, focus trap, Esc/×/backdrop close, focus returns to the headline.
const modal=document.createElement('div');modal.className='modal';document.body.append(modal);let opener=null;
function openModal(id,from){const h=D.modals[id];if(!h)return;opener=from;
  modal.className='modal open '+D.colors[id];
  modal.innerHTML=`<div class="box" role="dialog" aria-modal="true" aria-labelledby="mt"><button class="x" aria-label="${esc(T('a11y.modal_close'))}">${esc(T('modal.close_symbol'))}</button>${h.replace('tabindex="-1"','')}<p class="perma"><a href="${LP}/item/${id}.html">${esc(T('item.permalink'))}</a></p></div>`;
  document.body.classList.add('locked');[...document.body.children].forEach(n=>{if(n!==modal)n.inert=true});modal.querySelector('.x').focus()}
function closeModal(){if(!modal.classList.contains('open'))return;modal.className='modal';modal.innerHTML='';document.body.classList.remove('locked');[...document.body.children].forEach(n=>n.inert=false);opener&&opener.focus()}
modal.addEventListener('click',e=>{if(e.target===modal||e.target.closest('.x'))closeModal()});
modal.addEventListener('keydown',e=>{if(e.key=='Escape'){e.preventDefault();closeModal()}
  if(e.key=='Tab'){const f=[...modal.querySelectorAll('a[href],button')],a=f[0],z=f[f.length-1];
    if(e.shiftKey&&document.activeElement===a){e.preventDefault();z.focus()}else if(!e.shiftKey&&document.activeElement===z){e.preventDefault();a.focus()}}});
addEventListener('hashchange',()=>{closeModal();render()});
fetch(document.body.dataset.src||'data.json').then(r=>r.json()).then(d=>{D=d;render(true)}).catch(()=>{/* static HTML remains fully usable */});
})();

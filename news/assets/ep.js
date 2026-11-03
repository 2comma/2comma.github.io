/* Edition switch for days with both digests (Boa's .cal.split .eds-sw). Loaded on every page; no-JS shows both editions. */
document.documentElement.classList.add('js');
/* UI strings (window.TCN_T, set in <head> per language) with English fallback. */
const tcnT=(k,o={})=>((window.TCN_T||{})[k]||({'a11y.sections_more':'More sections','a11y.sections_prev':'Previous sections','a11y.collapse_section':'Collapse {section}','a11y.expand_section':'Expand {section}'})[k]||k).replace(/\{(\w+)\}/g,(m,n)=>n in o?o[n]:m);
/* Language switch (EN / 繁 / 简): remember the click in localStorage 'tcn-lang' (the English pages' <head> script redirects a saved zh-* choice
   before paint); carry the current #/view over so the same view opens in the other language. No browser-language auto-detection. */
document.addEventListener('click',e=>{const a=e.target.closest('.lang-sw a[data-lang]');if(!a)return;try{localStorage.setItem('tcn-lang',a.dataset.lang)}catch(_){}
  if(location.hash&&!a.href.includes('#'))a.href=a.href+location.hash});
document.addEventListener('click',e=>{const b=e.target.closest('.eds-sw .ep');if(!b)return;const hero=b.closest('.hero');
  hero.querySelectorAll('.ep').forEach(x=>{const on=x===b;x.classList.toggle('on',on);x.setAttribute('aria-selected',on)});
  hero.querySelectorAll('.edpanel').forEach(p=>p.toggleAttribute('data-off',p.dataset.ed!==b.dataset.ep))});
document.addEventListener('keydown',e=>{const b=e.target.closest&&e.target.closest('.eds-sw .ep');if(!b||!/Arrow(Up|Down|Left|Right)/.test(e.key))return;
  e.preventDefault();const all=[...b.parentNode.querySelectorAll('.ep')],n=all[(all.indexOf(b)+1)%all.length];n.focus();n.click()});
/* Theme toggle: initial theme set pre-paint by inline <head> script (localStorage), else prefers-color-scheme via CSS. */
document.addEventListener('click',e=>{if(!e.target.closest('.theme-tg'))return;const r=document.documentElement,
  cur=r.dataset.theme||(matchMedia('(prefers-color-scheme: light)').matches?'light':'dark'),nx=cur=='light'?'dark':'light';
  r.dataset.theme=nx;try{localStorage.setItem('tcn-theme',nx)}catch(_){}});
/* Section bar: chevrons + edge fade when tabs overflow (9 sections on mobile); keeps the current section in view. */
(()=>{const w=document.querySelector('.secnav-w'),n=w&&w.querySelector('.secnav');if(!n)return;
  const mk=(c,t,d)=>{const b=document.createElement('button');b.type='button';b.className='sn-more '+c;b.textContent=t;b.setAttribute('aria-label',tcnT(d>0?'a11y.sections_more':'a11y.sections_prev'));b.tabIndex=-1;
    b.addEventListener('click',()=>n.scrollBy({left:d*n.clientWidth*.7,behavior:'smooth'}));w.append(b)};
  mk('sn-l','‹',-1);mk('sn-r','›',1);
  const up=()=>{w.classList.toggle('ovl',n.scrollLeft>4);w.classList.toggle('ovr',n.scrollLeft+n.clientWidth<n.scrollWidth-4)};
  const on=n.querySelector('a.on');if(on&&on.offsetLeft+on.offsetWidth>n.clientWidth)n.scrollLeft=on.offsetLeft-n.clientWidth/2+on.offsetWidth/2;
  n.addEventListener('scroll',up,{passive:true});addEventListener('resize',up);up()})();
/* Collapsible landing sections (v4). State: localStorage 'tcn-collapsed' = JSON array of section keys.
   The <head> script mirrors it onto <html data-collapsed=" a b "> before first paint; CSS (sections.css) hides .lsec-b for those keys.
   Delegated handlers so it keeps working after app.js re-renders #view. No-JS: buttons hidden, everything expanded. */
(()=>{const r=document.documentElement,K='tcn-collapsed';
  const get=()=>(r.getAttribute('data-collapsed')||'').trim().split(/\s+/).filter(Boolean);
  const set=a=>{a=[...new Set(a)];a.length?r.setAttribute('data-collapsed',' '+a.join(' ')+' '):r.removeAttribute('data-collapsed');try{localStorage.setItem(K,JSON.stringify(a))}catch(_){}sync()};
  const sync=()=>{const c=get();document.querySelectorAll('.lsec-tg').forEach(b=>{const open=!c.includes(b.dataset.sec),n=b.closest('.lsec').querySelector('h2');
    b.setAttribute('aria-expanded',open);b.setAttribute('aria-label',tcnT(open?'a11y.collapse_section':'a11y.expand_section',{section:n?n.textContent.replace(/\s+/g,' ').trim():b.dataset.sec}))})};
  document.addEventListener('click',e=>{const b=e.target.closest('.lsec-tg');if(!b)return;const c=get(),k=b.dataset.sec;set(c.includes(k)?c.filter(x=>x!==k):c.concat(k))});
  addEventListener('storage',e=>{if(e.key!==K)return;let a=[];try{a=JSON.parse(e.newValue||'[]')}catch(_){}a.length?r.setAttribute('data-collapsed',' '+a.join(' ')+' '):r.removeAttribute('data-collapsed');sync()});
  const v=document.getElementById('view');v&&new MutationObserver(sync).observe(v,{childList:true});sync()})();
/* Landing block order (owner 2026-10-23): newest first by the newest deploy still inside the 48h window (section = its shown cards'
   data-exp, weekend block = its own data-exp); blocks with nothing left under 48h go last in SECTIONS order (data-i).
   build.py renders the build-time order; this redoes it on load and after app.js re-renders #view, as stories age out. */
(()=>{const run=()=>{const box=document.querySelector('.lblocks[data-win]');if(!box)return;const W=+box.dataset.win,n=Date.now()/1e3;
  const live=t=>t&&n-t<W?t:0;
  const key=s=>s.classList.contains('wkend')?live(+s.dataset.exp):Math.max(0,...[...s.querySelectorAll('[data-exp]')].map(c=>live(+c.dataset.exp)));
  const all=[...box.children].filter(s=>s.classList.contains('lsec')),k=new Map(all.map((s,i)=>[s,{t:key(s),i}]));
  const want=all.slice().sort((a,b)=>{const x=k.get(a),y=k.get(b);if(!x.t!==!y.t)return x.t?-1:1;if(x.t&&y.t&&x.t!==y.t)return y.t-x.t;
    if(!x.t&&!y.t)return (a.dataset.i??99)-(b.dataset.i??99)||x.i-y.i;return x.i-y.i});
  if(want.some((s,i)=>s!==all[i]))want.forEach(s=>box.append(s))};
  run();const v=document.getElementById('view');v&&new MutationObserver(run).observe(v,{childList:true})})();

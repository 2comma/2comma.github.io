fetch('counts.json?t='+Date.now(),{cache:'no-store'}).then(r=>r.ok?r.json():null).then(d=>{
 const u=document.getElementById('upd'); if(!d){u.textContent='New-message counts unavailable right now.';return}
 let total=0; document.querySelectorAll('.card[data-dm]').forEach(c=>{const n=(d.counts||{})[c.dataset.dm]|0; const b=c.querySelector('.badge'); if(n>0){b.textContent=n>99?'99+':n;b.hidden=false;total+=n}});
 u.textContent=(total?total+' new message'+(total>1?'s':''):'No new messages')+' \u00b7 counts as of '+d.updated+' (refreshes hourly, weekdays 8 AM\u20135 PM PT)';
 if(total) document.title='('+total+') TwoComma Slack';
}).catch(()=>{});

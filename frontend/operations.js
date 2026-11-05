const $=s=>document.querySelector(s);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function params(){return new URLSearchParams({start_period:$('#start').value,end_period:$('#end').value,currency:$('#currency').value})}
async function api(path,body){let r=await fetch('/api/v1/'+path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});let v=await r.json();if(!r.ok)throw Error(v.error?.message||JSON.stringify(v));return v}
function show(target,data){let box=$(target);if(Array.isArray(data)&&data.length){let keys=Object.keys(data[0]);box.innerHTML='<div class="scroll"><table><thead><tr>'+keys.map(k=>'<th>'+esc(k)+'</th>').join('')+'</tr></thead><tbody>'+data.map(row=>'<tr>'+keys.map(k=>'<td>'+esc(typeof row[k]==='object'?JSON.stringify(row[k]):row[k])+'</td>').join('')+'</tr>').join('')+'</tbody></table></div>'}else{box.textContent=Array.isArray(data)?'没有符合条件的记录。':JSON.stringify(data,null,2);box.style.whiteSpace='pre-wrap'}}
async function act(fn){$('#message').textContent='执行中…';try{await fn();$('#message').textContent='已完成'}catch(e){$('#message').textContent=e.message}}
$('#analyze').onclick=()=>act(async()=>{let p=Object.fromEntries(params());let d=await api('analysis',{...p,question:$('#question').value,mode:'demo'});$('#answer').textContent=d.answer+'\n\n任务编号：'+d.task_id+'\n风险规则：'+JSON.stringify(d.risks)+'\n工具记录：'+JSON.stringify(d.tool_calls)});
$('#knowledge').onclick=()=>act(async()=>{$('#answer').textContent=JSON.stringify(await api('knowledge/search?q='+encodeURIComponent($('#question').value)),null,2)});
$('#register').onsubmit=e=>{e.preventDefault();act(async()=>{let data=Object.fromEntries(new FormData(e.target));data.currency=$('#currency').value;if(!data.due_date)data.due_date=null;let value=await api('finance/registers',data);show('#finance-result',value)})};
$('#budget').onclick=()=>act(async()=>show('#finance-result',await api('finance/budget?'+params())));
for(const kind of ['receivable','payable'])$('#'+kind).onclick=()=>act(async()=>{let data=await api('finance/aging?'+new URLSearchParams({currency:$('#currency').value,as_of:$('#asof').value,kind}));show('#finance-result',data.rows);$('#message').textContent=data.basis});
$('#risks').onclick=()=>act(async()=>{let data=await api('risks?'+params()+'&as_of='+encodeURIComponent($('#asof').value));show('#governance-result',data.items)});
$('#dictionary').onclick=()=>act(async()=>show('#governance-result',await api('governance/dictionary')));
$('#audit').onclick=()=>act(async()=>show('#governance-result',await api('audit')));
$('#lineage').onclick=()=>act(async()=>show('#lineage-result',await api('governance/lineage/'+encodeURIComponent($('#batchid').value))));

import {lines} from '../api/research.js';
import {table} from '../components/common/table.js';
import {esc} from '../utils/format.js';
import {bindForm} from '../hooks/forms.js';
import {LINE_STATES,PIECE_STATES,JUDGMENTS} from '../types/enums.js';
let lineId=0,editor=[],current=null,lastClaim=null;
const roster=()=>editor.map(p=>({shift:p.shift.trim(),roll:p.roll.trim()}));
function editorHtml(){return `<div class="roster">${editor.length?editor.map((p,i)=>`<div class="roster-row"><span class="seq">${i+1}</span><input data-shift="${i}" placeholder="班次，如 早班" value="${esc(p.shift)}" maxlength="40"><input data-roll="${i}" placeholder="卷号，如 卷-07" value="${esc(p.roll)}" maxlength="40"><button type="button" class="text" data-remove="${i}">移除</button></div>`).join(''):'<p>尚未登记试件，点下方「+ 添加试件」按加工顺序逐件登记。</p>'}</div><div class="toolbar"><button type="button" class="secondary" id="add-piece" ${editor.length>=32?'disabled':''}>+ 添加试件</button><small>已登记 ${editor.length}/32 件 · 每班和每卷各自 A/B 件数相等 · 同工艺连续至多两件</small></div>`;}
function lineHtml(cur,held,writable,station){
 const done=cur.status==='completed',mine=held&&station&&held.station===station;
 return `<section class="strip"><span>${LINE_STATES[cur.status]||cur.status}</span><span>名单第 ${cur.version} 版</span><span>已判定 ${cur.judged_count}/${cur.piece_count} 件</span></section>
 ${lastClaim?`<section class="result-intro"><strong>第${lastClaim.seq}件 · 工艺 ${lastClaim.process}</strong><p>${esc(lastClaim.shift)} · ${esc(lastClaim.roll)} · 工位「${esc(lastClaim.station)}」${lastClaim.reused?' · 断线重试，返回原领取结果':''}</p></section>`:''}
 ${held?`<h2>当前在制 <small>交回判定后才揭下一件</small></h2><div class="method-note"><strong>第${held.seq}件 · 工艺 ${held.process}</strong><p>${esc(held.shift)} · ${esc(held.roll)} · 工位「${esc(held.station)}」待交回判定</p></div>`:''}
 ${writable&&!done?`<h2>领工艺</h2><form id="claim-form" class="inline-form"><label>工位<input name="station" value="${esc(station)}" required maxlength="40" placeholder="如 1号工位"></label><button type="submit">领取下一件 →</button></form><p><small>两工位同时领取只派一方；断线后同工位重试返回原领取结果，不重复派工。</small></p>`:''}
 ${mine?`<h2>交判定</h2><form id="judge-form" class="inline-form"><input type="hidden" name="seq" value="${held.seq}"><input type="hidden" name="station" value="${esc(held.station)}"><label>判定<select name="judgment">${JUDGMENTS.map(j=>`<option>${j}</option>`).join('')}</select></label><button type="submit">交回第${held.seq}件判定 →</button></form>`:''}
 ${done?'<div class="method-note">本批已完工，全部工艺已公开。</div>':''}
 <h2>名单与进度 <small>完工前未派工艺保密</small></h2>
 ${table(['序号','班次','卷号','状态','工艺','工位','判定'],cur.pieces.map(p=>[p.seq,p.shift,p.roll,PIECE_STATES[p.status]||p.status,p.process||'未派',p.station||'—',p.judgment||'—']))}`;
}
function registerHtml(cur){return `<h2>登记名单 <small>按加工顺序逐件登记；提交即抽排，派不了会说明原因</small></h2>${editorHtml()}<form id="line-form" class="inline-form"><label>新批名称<input name="name" minlength="2" maxlength="120" required placeholder="如 砚田·连续试封一批"></label><button type="submit">登记新批并抽排 →</button></form>${cur&&cur.status==='registering'?`<h2>整批更正 <small>首件发出前有效；名单与排法按同一版锁定</small></h2><form id="correct-form" class="inline-form"><button type="button" class="secondary" id="load-current">载入「${esc(cur.name)}」当前名单</button><button type="submit">整批更正为第${cur.version+1}版 →</button></form><p><small>首件发出后名单与排法锁定，不可更正；并发更正时慢的一方会收到版本提示。</small></p>`:''}`;}
export async function render(){
 const list=await lines.list();
 if(lineId && !list.some(x=>x.id===lineId)) lineId=0;
 if(!lineId && list.length) lineId=list[0].id;
 current=lineId?await lines.get(lineId):null;
 const writable=localStorage.getItem('research-role')!=='viewer';
 const station=localStorage.getItem('seal-station')||'';
 const held=current?current.pieces.find(p=>p.status==='claimed'):null;
 return `<div class="eyebrow">06 / SEAL LINE DISPATCH</div><h1>连续试封派工</h1><p class="lead">连续试封时前一工艺会影响下一件：先按加工顺序登记试件的班次和卷号，系统从全部合规整线排法中等概率抽一套，逐件派发，交回判定才揭下一件。</p><div class="method-note">每班和每卷各自 A/B 件数相等 · 同工艺连续至多两件 · 最多32件 · 无解或搜索超5秒拒绝派工 · 首件发出前可整批更正 · 完工前未派工艺保密</div><div class="toolbar"><label>派工批<select id="line-select">${list.map(x=>`<option value="${x.id}" ${x.id===lineId?'selected':''}>#${x.id} ${esc(x.name)} · ${LINE_STATES[x.status]||x.status} · ${x.judged_count}/${x.piece_count}</option>`).join('')}</select></label><button id="refresh-line" class="secondary">刷新</button></div>${current?lineHtml(current,held,writable,station):'<p>尚无派工批，请在下方登记名单。</p>'}${writable?registerHtml(current):'<p class="method-note">观察员可查看进度；登记、领取与判定由分析师或负责人操作。</p>'}`;
}
export function bind(refresh){
 const sel=document.getElementById('line-select');
 if(sel) sel.onchange=()=>{lineId=+sel.value;lastClaim=null;refresh();};
 const rb=document.getElementById('refresh-line');
 if(rb) rb.onclick=()=>refresh();
 document.querySelectorAll('[data-shift]').forEach(el=>el.oninput=()=>editor[+el.dataset.shift].shift=el.value);
 document.querySelectorAll('[data-roll]').forEach(el=>el.oninput=()=>editor[+el.dataset.roll].roll=el.value);
 document.querySelectorAll('[data-remove]').forEach(el=>el.onclick=()=>{editor.splice(+el.dataset.remove,1);refresh();});
 const add=document.getElementById('add-piece');
 if(add) add.onclick=()=>{if(editor.length<32){editor.push({shift:'',roll:''});refresh();}};
 const loadCur=document.getElementById('load-current');
 if(loadCur) loadCur.onclick=()=>{editor=current.pieces.map(p=>({shift:p.shift,roll:p.roll}));refresh();};
 bindForm('line-form',async data=>{const r=await lines.create({name:data.name,pieces:roster()});lineId=r.id;editor=[];lastClaim=null;refresh();});
 bindForm('correct-form',async()=>{await lines.correct(lineId,{version:current.version,pieces:roster()});lastClaim=null;refresh();});
 bindForm('claim-form',async data=>{const station=data.station.trim();localStorage.setItem('seal-station',station);lastClaim=await lines.claim(lineId,{station});refresh();});
 bindForm('judge-form',async data=>{await lines.judge(lineId,{station:data.station,seq:+data.seq,judgment:data.judgment});lastClaim=null;refresh();});
}

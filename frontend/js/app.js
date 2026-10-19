import { getLanguage, setLanguage, applyLanguage, initLanguagePreference, t } from "./i18n.js";
const API = "/api";
const $ = (selector, root=document) => root.querySelector(selector);
const $$ = (selector, root=document) => [...root.querySelectorAll(selector)];
const state = { districts: [], districtId: localStorage.getItem("mazhai-district") || "chennai", forecast: null, history: null, map: null, markers: new Map(), historyChart: null, detailChart: null, comparisonChart: null, lastView: "overview", chatHistory: [], asking: false };
const views = ["overview","live","history","districts","forecast","analytics","assistant","sources","settings"];
const today = new Date();
const dateISO = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}-${String(d.getDate()).padStart(2,"0")}`;
const daysAgo = n => { const d=new Date(); d.setDate(d.getDate()-n); return dateISO(d); };
const escapeHTML = value => String(value ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const district = id => state.districts.find(d=>d.id===id);
function toast(message){const el=$("#toast");el.textContent=message;el.classList.add("show");clearTimeout(toast.timer);toast.timer=setTimeout(()=>el.classList.remove("show"),3200);}
async function api(path, options={}) {
  const response=await fetch(`${API}${path}`,{headers:{"Content-Type":"application/json",...(options.headers||{})},...options});
  let data; try{data=await response.json()}catch{data={detail:"Invalid server response"}}
  if(!response.ok){const detail=typeof data.detail==="string"?data.detail:Array.isArray(data.detail)?data.detail.map(x=>x.msg).join("; "):(data.detail?.message||data.message||`Request failed (${response.status})`);throw new Error(detail)}
  return data;
}
function showView(name){
  if(!views.includes(name)) return;
  $$(".view").forEach(el=>el.classList.toggle("active",el.id===`view-${name}`));
  $$(".nav-item[data-view]").forEach(el=>el.classList.toggle("active",el.dataset.view===name));
  $("#page-title").textContent=({overview:"Overview",live:"Live weather",history:"Rainfall history",districts:"District explorer",forecast:"Forecast & risk",analytics:"Rainfall analytics",assistant:"AI weather assistant",sources:"Data sources",settings:"Settings"})[name];
  $("#sidebar").classList.remove("open"); state.lastView=name;
  if(name==="live") loadLive();
  if(name==="forecast") loadForecastDetail();
  if(name==="districts") renderDistricts();
  if(name==="sources") loadSources();
  if(name==="assistant") $("#ai-context-district").textContent=district(state.districtId)?.name||"Not selected";
}
function populateDistrictSelects(){
  const selects=[$("#district-select"),...$$(".district-select-sync"),$("#default-district")].filter(Boolean);
  for(const sel of selects){
    const selected=sel.id==="default-district"?(localStorage.getItem("mazhai-district")||"chennai"):state.districtId;
    sel.innerHTML=state.districts.map(d=>`<option value="${d.id}">${escapeHTML(d.name)}</option>`).join("");
    sel.value=selected;
  }
}
function selectDistrict(id){
  if(!district(id)) return;
  if(state.districtId!==id)state.chatHistory=[];
  state.districtId=id;localStorage.setItem("mazhai-district",id);
  $("#district-select").value=id;
  $$(".district-select-sync").forEach(s=>s.value=id);
  $("#ai-context-district").textContent=district(id).name;
  loadOverview();
}
function fmt(v,digits=1){return typeof v==="number"&&Number.isFinite(v)?v.toFixed(digits):"—";}
function showFreshness(data){return `${data?.stale?"Stale cached data":data?.cached?"Cached provider data":"Retrieved"}${data?.retrieved_at?` · ${new Date(data.retrieved_at).toLocaleString()}`:""}`;}
function chartOptions(){return {responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false},tooltip:{backgroundColor:"#102438",titleColor:"#eaf3fb",bodyColor:"#b4c8d8",borderColor:"#29445a",borderWidth:1,displayColors:false}},scales:{x:{grid:{display:false},ticks:{color:"#748ba0",font:{size:9},maxTicksLimit:9},border:{display:false}},y:{beginAtZero:true,grid:{color:"#1b2d3f"},ticks:{color:"#748ba0",font:{size:9}},border:{display:false}}}};}
function drawChart(canvasId, existingKey, labels, values, label="Precipitation (mm)"){
  if(!window.Chart) return null;
  if(state[existingKey])state[existingKey].destroy();
  const ctx=$(`#${canvasId}`);if(!ctx)return null;
  state[existingKey]=new Chart(ctx,{type:"bar",data:{labels,datasets:[{label,data:values,backgroundColor:"rgba(75,213,232,.68)",hoverBackgroundColor:"#4bd5e8",borderRadius:4,maxBarThickness:18}]},options:chartOptions()});
  return state[existingKey];
}
function setChartEmpty(id,empty){const el=$(`#${id}`);if(el)el.classList.toggle("hidden",!empty);}
async function loadOverview(){
  const d=district(state.districtId);if(!d)return;
  $("#outlook-location").textContent=d.name;
  $("#metric-temp-foot").textContent=`${d.name} · provider model`;
  try{
    const f=await api(`/weather/forecast?district_id=${encodeURIComponent(d.id)}`);
    state.forecast=f;renderForecastMetrics(f);renderOutlook(f);renderSignal(f);renderMapForecast(f);
    $("#forecast-source-note").textContent=`${f.source} · ${showFreshness(f)}`;
    $("#sidebar-status").textContent=f.stale?"Showing cached data":"Provider reachable";
  }catch(e){
    ["metric-temp","metric-rain","metric-humidity","metric-seven-day"].forEach(id=>{$(`#${id}`).innerHTML="—";});
    $("#outlook-list").innerHTML=`<div class="empty-state compact">${escapeHTML(e.message)}<br>Retry when the provider is available.</div>`;
    $("#forecast-source-note").textContent="No verified forecast currently available";
    $("#sidebar-status").textContent="Weather data unavailable";
    renderSignal(null);
  }
  try{const h=await api(`/rainfall/history?district_id=${d.id}&start=${daysAgo(29)}&end=${dateISO(today)}`);state.history=h;renderHistoryMini(h)}
  catch(e){$("#history-chart-empty").textContent=`Historical data unavailable: ${e.message}`;setChartEmpty("history-chart-empty",true)}
}
function renderForecastMetrics(f){
  const c=f.current||{}, total=(f.daily||[]).reduce((sum,x)=>sum+(typeof x.precipitation_mm==="number"?x.precipitation_mm:0),0);
  $("#metric-temp").innerHTML=`${fmt(c.temperature_c)}<small>°C</small>`;
  $("#metric-rain").innerHTML=`${fmt(c.precipitation_mm)}<small> mm</small>`;
  $("#metric-humidity").innerHTML=`${fmt(c.humidity_pct,0)}<small>%</small>`;
  $("#metric-seven-day").innerHTML=`${fmt(total)}<small> mm</small>`;
  $("#metric-seven-foot").textContent=`${(f.daily||[]).length}-day provider precipitation sum`;
}
function renderOutlook(f){
  const days=f.daily||[];
  if(!days.length){$("#outlook-list").innerHTML='<div class="empty-state compact">Provider returned no daily forecast values.</div>';return}
  const max=Math.max(1,...days.map(d=>d.precipitation_mm||0));
  $("#outlook-list").innerHTML=days.slice(0,7).map((d,i)=>`<div class="outlook-row"><div class="outlook-day">${i===0?"Today":new Date(`${d.date}T12:00:00`).toLocaleDateString("en-IN",{weekday:"short"})}<small>${d.date.slice(5)}</small></div><div><div class="outlook-bar"><span style="width:${Math.max(0,Math.min(100,(d.precipitation_mm||0)/max*100))}%"></span></div><small class="muted">${d.precipitation_probability_pct==null?"Probability not provided":`${fmt(d.precipitation_probability_pct,0)}% chance`}</small></div><div class="outlook-rain">${fmt(d.precipitation_mm)}<small>mm</small></div></div>`).join("");
}
function renderSignal(f){
  if(!f){$("#signal-content").innerHTML='<div class="signal-empty">No current forecast data is available. The app will not generate a synthetic signal.</div>';return}
  const days=f.daily||[], wet=days.filter(d=>(d.precipitation_mm||0)>=1), total=days.reduce((s,d)=>s+(d.precipitation_mm||0),0), peak=days.reduce((a,b)=>(b.precipitation_mm||0)>(a.precipitation_mm||0)?b:a,days[0]||{});
  const items=[
    ["↗","7-day precipitation",`${fmt(total)} mm forecast total from ${f.source}. This is a model forecast, not a measured district total.`],
    ["◷","Rainfall timing",wet.length?`${wet.length} of ${days.length} forecast days have at least 1 mm indicated. Highest daily amount: ${fmt(peak.precipitation_mm)} mm on ${peak.date}.`:"No forecast day reaches 1 mm in the returned daily data; this does not guarantee dry conditions."],
    ["i","What this means","This is a rainfall indicator only. Flooding depends on drainage, terrain, rivers, soil moisture, and local conditions."]
  ];
  $("#signal-content").innerHTML=items.map(([icon,title,desc])=>`<div class="signal-item"><span class="signal-bullet">${icon}</span><div><b>${title}</b>${escapeHTML(desc)}</div></div>`).join("");
}
function renderHistoryMini(h){
  const records=h.records||[], values=records.map(r=>r.precipitation_mm);
  setChartEmpty("history-chart-empty",!records.length);
  if(records.length)drawChart("history-chart","historyChart",records.map(r=>r.date.slice(5)),values);
}
function initMap(){
  if(!window.L||state.map)return;
  state.map=L.map("tn-map",{zoomControl:true,scrollWheelZoom:false}).setView([10.85,78.5],6);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",{maxZoom:18,attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'}).addTo(state.map);
  state.districts.forEach(d=>{
    const marker=L.circleMarker([d.lat,d.lon],{radius:5,weight:1,color:"#07111f",fillColor:"#71869b",fillOpacity:.9}).addTo(state.map);
    marker.bindPopup(`<b>${escapeHTML(d.name)}</b><br><span>Loading forecast data on selection</span><br><button data-map-district="${d.id}">Explore district</button>`);
    marker.on("click",()=>{state.map.closePopup();});
    state.markers.set(d.id,marker);
  });
  $("#tn-map").addEventListener("click",e=>{const btn=e.target.closest("[data-map-district]");if(btn){selectDistrict(btn.dataset.mapDistrict);showView("districts")}});
  setTimeout(()=>state.map.invalidateSize(),120);
}
function renderMapForecast(f){
  const marker=state.markers.get(f.district.id);if(!marker)return;
  const total=(f.daily||[]).reduce((s,d)=>s+(d.precipitation_mm||0),0);
  const color=total>=50?"#f1b65b":total>=10?"#4bd5e8":"#39c6b2";
  marker.setStyle({fillColor:color,radius:8,fillOpacity:.95});
  marker.setPopupContent(`<b>${escapeHTML(f.district.name)}</b><br>7-day forecast total: ${fmt(total)} mm<br><small>Open-Meteo model data · representative coordinates</small><br><button data-map-district="${f.district.id}">Explore district</button>`);
}
async function loadLive(){
  const d=district(state.districtId);if(!d)return;
  $("#live-content").innerHTML='<div class="panel empty-state">Loading provider conditions…</div>';
  try{
    const f=await api(`/weather/forecast?district_id=${d.id}`),c=f.current||{};
    const fields=[["Relative humidity",`${fmt(c.humidity_pct,0)}%`],["Current precipitation",`${fmt(c.precipitation_mm)} mm`],["Wind speed",`${fmt(c.wind_kmh)} km/h`],["Wind direction",`${fmt(c.wind_direction_deg,0)}°`],["Cloud cover",`${fmt(c.cloud_cover_pct,0)}%`],["Forecast model timezone",f.model_timezone||"—"]];
    $("#live-content").innerHTML=`<article class="panel weather-detail"><h2>${escapeHTML(d.name)} · current</h2><div class="weather-big">${fmt(c.temperature_c)}°</div><div class="weather-sub">Air temperature · Celsius</div><div style="margin-top:18px">${fields.slice(0,3).map(([k,v])=>`<div class="weather-kv"><span>${k}</span><b>${v}</b></div>`).join("")}</div></article><article class="panel weather-detail"><h2>Atmospheric conditions</h2><div class="weather-big">${fmt(c.humidity_pct,0)}<small style="font:400 14px var(--font);color:var(--muted)"> % RH</small></div><div class="weather-sub">Relative humidity</div><div style="margin-top:18px">${fields.slice(3).map(([k,v])=>`<div class="weather-kv"><span>${k}</span><b>${v}</b></div>`).join("")}</div></article><article class="panel weather-detail"><h2>Data provenance</h2><div class="weather-sub">Provider and retrieval metadata</div><div style="margin-top:18px"><div class="weather-kv"><span>Source</span><b>Open-Meteo</b></div><div class="weather-kv"><span>Retrieved at</span><b>${f.retrieved_at?new Date(f.retrieved_at).toLocaleTimeString():"—"}</b></div><div class="weather-kv"><span>Data status</span><b>${f.stale?"Stale cache":f.cached?"Cached":"Fresh response"}</b></div><div class="weather-kv"><span>Coordinate type</span><b>District reference point</b></div></div><a href="${f.source_url}" target="_blank" rel="noreferrer">Provider documentation ↗</a></article>`;
  }catch(e){$("#live-content").innerHTML=`<div class="panel empty-state">${escapeHTML(e.message)}</div>`}
}
async function loadForecastDetail(){
  const d=district(state.districtId);if(!d)return;
  $("#forecast-detail").innerHTML='<div class="empty-state">Loading forecast…</div>';
  try{
    const f=await api(`/weather/forecast?district_id=${d.id}`),c=f.current||{},days=f.daily||[];
    const total=days.reduce((s,x)=>s+(x.precipitation_mm||0),0);
    $("#forecast-detail").innerHTML=`<div class="forecast-top"><div><h2>${escapeHTML(d.name)}</h2><p>Provider forecast · representative district coordinates</p><p style="margin-top:8px">${escapeHTML(f.source)} · ${f.stale?"cached/stale":f.cached?"cached":"retrieved"}</p></div><div style="text-align:right"><div class="forecast-now">${fmt(c.temperature_c)}°C</div><p class="muted" style="font-size:10px;margin:0">Current temperature</p><p style="font-size:10px;color:var(--cyan);margin:5px 0 0">${fmt(total)} mm / 7 days</p></div></div><div class="forecast-days">${days.map((day,i)=>`<div class="forecast-day"><small>${i===0?"Today":new Date(`${day.date}T12:00:00`).toLocaleDateString("en-IN",{weekday:"short"})}</small><div class="rain-emoji">${(day.precipitation_mm||0)>=10?"🌧":(day.precipitation_mm||0)>=1?"🌦":"☁"}</div><b>${fmt(day.temp_max_c,0)}° / ${fmt(day.temp_min_c,0)}°</b><span>${fmt(day.precipitation_mm)} mm</span><small style="margin-top:5px">${day.precipitation_probability_pct==null?"—":`${fmt(day.precipitation_probability_pct,0)}% chance`}</small></div>`).join("")}</div><div class="forecast-meta"><span>Source: ${escapeHTML(f.source)}</span><span>Updated: ${f.retrieved_at?new Date(f.retrieved_at).toLocaleString():"—"}</span><span>7-day sum is a model output, not a warning</span></div>`;
  }catch(e){$("#forecast-detail").innerHTML=`<div class="empty-state">${escapeHTML(e.message)}</div>`}
}
function renderDistricts(filter=""){
  const query=filter.trim().toLowerCase(),items=state.districts.filter(d=>d.name.toLowerCase().includes(query)||d.id.includes(query));
  $("#district-count").textContent=`${items.length} of ${state.districts.length} districts`;
  $("#district-grid").innerHTML=items.map(d=>`<button class="district-card" data-district-card="${d.id}"><div class="district-card-top"><span class="district-initial">${escapeHTML(d.name.slice(0,2).toUpperCase())}</span><small>District reference point</small></div><b>${escapeHTML(d.name)}</b><span class="district-coordinate">${d.lat.toFixed(3)}° N · ${d.lon.toFixed(3)}° E</span><div class="district-status"><i class="status-ring"></i> Weather loads on selection</div></button>`).join("")||'<div class="empty-state">No matching district.</div>';
}
async function loadHistory(){
  const id=$("#history-district").value||state.districtId,start=$("#history-start").value,end=$("#history-end").value;
  if(!start||!end){toast("Choose both a start and end date.");return}
  if(end<start){toast("End date must be on or after start date.");return}
  $("#history-summary").innerHTML='<div class="panel empty-state">Loading historical data…</div>';
  try{
    const h=await api(`/rainfall/history?district_id=${id}&start=${start}&end=${end}`);state.history=h;
    const vals=h.records.map(r=>r.precipitation_mm).filter(v=>typeof v==="number"),wet=vals.filter(v=>v>=1),total=vals.length?vals.reduce((s,v)=>s+v,0):null,max=vals.length?Math.max(...vals):null;
    const cards=[["Total precipitation",total===null?"—":`${fmt(total)} mm`],["Wet days (≥1 mm)",`${wet.length}`],["Daily maximum",max===null?"—":`${fmt(max)} mm`],["Valid daily values",`${vals.length} / ${h.records.length}`]];
    $("#history-summary").innerHTML=cards.map(([k,v])=>`<article class="metric-card"><div class="metric-top"><span>${k}</span></div><div class="metric-value" style="font-size:24px">${v}</div><div class="metric-foot">${escapeHTML(district(id)?.name||id)}</div></article>`).join("");
    $("#history-chart-subtitle").textContent=`${district(id)?.name} · ${start} to ${end}`;
    setChartEmpty("history-detail-empty",!h.records.length);
    if(h.records.length)drawChart("history-detail-chart","detailChart",h.records.map(r=>r.date),h.records.map(r=>r.precipitation_mm));
    $("#history-source").textContent=`${h.source} · ${showFreshness(h)} · Historical grid/reanalysis estimate, not direct station observation.`;
    $("#export-csv").disabled=!h.records.length;toast(`Loaded ${h.records.length} daily records.`);
  }catch(e){$("#history-summary").innerHTML=`<div class="panel empty-state">${escapeHTML(e.message)}</div>`;$("#history-detail-empty").textContent="No verified data available for this selection.";setChartEmpty("history-detail-empty",true)}
}
function exportCSV(){
  if(!state.history?.records?.length){toast("Load history before exporting.");return}
  const h=state.history,rows=[["date","precipitation_mm","district_id","source"],...h.records.map(r=>[r.date,r.precipitation_mm??"",h.district.id,h.source])];
  const csv=rows.map(row=>row.map(v=>`"${String(v).replace(/"/g,'""')}"`).join(",")).join("\r\n");
  const url=URL.createObjectURL(new Blob([csv],{type:"text/csv;charset=utf-8"})),a=document.createElement("a");a.href=url;a.download=`mazhai-${h.district.id}-${h.records[0].date}-${h.records.at(-1).date}.csv`;a.click();URL.revokeObjectURL(url);
}
async function loadComparison(){
  const start=$("#analytics-start").value,end=$("#analytics-end").value;
  if(!start||!end||end<start){toast("Choose a valid date range.");return}
  $("#comparison-status").textContent="Loading historical estimates for 38 district reference points. This may take a little while…";
  $("#comparison-empty").textContent="Retrieving data…";setChartEmpty("comparison-empty",true);
  try{
    const result=await api(`/analytics/district-comparison?start=${start}&end=${end}`);
    const valid=result.districts.filter(d=>d.total_mm!==null).sort((a,b)=>b.total_mm-a.total_mm);
    if(state.comparisonChart)state.comparisonChart.destroy();
    state.comparisonChart=new Chart($("#comparison-chart"),{type:"bar",data:{labels:valid.map(d=>d.district),datasets:[{data:valid.map(d=>d.total_mm),backgroundColor:"rgba(75,213,232,.68)",borderRadius:3,maxBarThickness:22}]},options:{...chartOptions(),indexAxis:"y",scales:{x:{beginAtZero:true,grid:{color:"#1b2d3f"},ticks:{color:"#748ba0",font:{size:9}},border:{display:false}},y:{grid:{display:false},ticks:{color:"#9cb0c2",font:{size:9}},border:{display:false}}}}});
    $("#comparison-status").textContent=`${result.successful_districts}/38 districts returned values. ${result.note}`;
    $("#comparison-table-wrap").innerHTML=`<div class="panel-header"><div><h2>District totals</h2><p>Sorted by returned precipitation total</p></div></div><div class="table-scroll"><table class="data-table"><thead><tr><th>District</th><th>Total (mm)</th><th>Valid days</th><th>Status</th></tr></thead><tbody>${result.districts.sort((a,b)=>(b.total_mm??-1)-(a.total_mm??-1)).map(d=>`<tr><td>${escapeHTML(d.district)}</td><td>${d.total_mm===null?"—":fmt(d.total_mm)}</td><td>${d.valid_days}</td><td>${d.error?`Unavailable (${escapeHTML(d.error)})`:"Retrieved"}</td></tr>`).join("")}</tbody></table></div>`;
    toast(`Comparison completed: ${result.successful_districts}/38 districts.`);
  }catch(e){$("#comparison-status").textContent=e.message;setChartEmpty("comparison-empty",true);$("#comparison-empty").textContent=e.message}
}
async function loadSources(){
  $("#source-cards").innerHTML='<div class="panel empty-state">Loading source status…</div>';
  try{
    const s=await api("/sources/status");
    $("#source-cards").innerHTML=s.providers.map(p=>`<article class="source-card"><div class="source-card-top"><div><h2>${escapeHTML(p.name)}</h2><span class="source-kind">${escapeHTML(p.kind)}</span></div><span class="source-status ${p.status==="not_integrated"?"offline":""}">${p.status==="configured"?"CONFIGURED":"NOT INTEGRATED"}</span></div><p>${escapeHTML(p.notes)}</p><a href="${p.url}" target="_blank" rel="noreferrer">Documentation ↗</a></article>`).join("");
    $("#stored-source-table").innerHTML=s.stored_history.length?`<div class="table-scroll"><table class="data-table"><thead><tr><th>Source</th><th>Stored records</th><th>Latest retrieval</th></tr></thead><tbody>${s.stored_history.map(r=>`<tr><td>${escapeHTML(r.source)}</td><td>${r.records}</td><td>${escapeHTML(r.latest||"—")}</td></tr>`).join("")}</tbody></table></div>`:'<div class="empty-state">No historical observations stored yet. Load a historical date range to ingest records.</div>';
  }catch(e){$("#source-cards").innerHTML=`<div class="panel empty-state">${escapeHTML(e.message)}</div>`}
}
function renderInlineMarkdown(value){
  // Some model answers escape Markdown delimiters (`\\*\\*`) before placing
  // text in JSON. Normalize those delimiters, then escape every text segment
  // individually so formatting is consistent without trusting model HTML.
  const source=String(value??"").replace(/\\([*_\x60])/g,"$1");
  const tokens=source.split(/(\*\*[^*]+?\*\*|__[^_]+?__|\x60[^\x60]+\x60|\*[^*\n]+\*)/g);
  return tokens.map(token=>{
    if(/^\*\*[^*]+?\*\*$/.test(token))return "<strong>"+escapeHTML(token.slice(2,-2))+"</strong>";
    if(/^__[^_]+?__$/.test(token))return "<strong>"+escapeHTML(token.slice(2,-2))+"</strong>";
    if(/^\x60[^\x60]+\x60$/.test(token))return "<code>"+escapeHTML(token.slice(1,-1))+"</code>";
    if(/^\*[^*\n]+\*$/.test(token))return "<em>"+escapeHTML(token.slice(1,-1))+"</em>";
    return escapeHTML(token);
  }).join("");
}
function renderMarkdown(message){
  const lines=String(message??"").replace(/\r\n?/g,"\n").split("\n");
  const html=[];let paragraph=[];let listType=null;let listItems=[];
  const flushParagraph=()=>{if(paragraph.length){html.push("<p>"+paragraph.map(renderInlineMarkdown).join(" ")+"</p>");paragraph=[]}};
  const flushList=()=>{if(listType){html.push("<"+listType+">"+listItems.join("")+"</"+listType+">");listType=null;listItems=[]}};
  const closeBlocks=()=>{flushParagraph();flushList()};
  for(const raw of lines){
    const line=raw.trim();
    if(!line){closeBlocks();continue}
    if(/^[-*_]{3,}$/.test(line)){closeBlocks();html.push("<hr>");continue}
    const heading=line.match(/^(#{1,6})\s+(.+)$/);
    if(heading){closeBlocks();const tag=heading[1].length<=2?"h4":"h5";html.push("<"+tag+">"+renderInlineMarkdown(heading[2])+"</"+tag+">");continue}
    const bullet=line.match(/^[-*+]\s+(.+)$/);
    const ordered=line.match(/^\d+[.)]\s+(.+)$/);
    if(bullet||ordered){
      flushParagraph();const type=bullet?"ul":"ol";
      if(listType&&listType!==type)flushList();
      if(!listType)listType=type;
      listItems.push("<li>"+renderInlineMarkdown((bullet||ordered)[1])+"</li>");
      continue;
    }
    const quote=line.match(/^>\s?(.*)$/);
    if(quote){closeBlocks();html.push("<blockquote>"+renderInlineMarkdown(quote[1])+"</blockquote>");continue}
    if(listType)flushList();
    paragraph.push(line);
  }
  closeBlocks();
  return html.join("");
}
function renderAssistantReply(container,result,reply){
  container.replaceChildren();
  if(result?.alert){
    const alert=result.alert;
    const level=String(alert.level||"Unable to assess");
    const slug=level.toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"")||"unknown";
    const card=document.createElement("section");card.className="ai-alert-card ai-alert-"+slug;
    const head=document.createElement("div");head.className="ai-alert-head";
    const title=document.createElement("strong");title.className="ai-alert-title";title.textContent="Rainfall attention · "+(result?.location?result.location+" · ":"")+level;
    const badge=document.createElement("span");badge.className="ai-alert-badge";badge.textContent="APP INDICATOR · NOT OFFICIAL";
    head.append(title,badge);
    const rationale=document.createElement("p");rationale.className="ai-alert-rationale";rationale.textContent=alert.rationale||"The available evidence could not determine an attention level.";
    const note=document.createElement("p");note.className="ai-alert-note";note.textContent="Preliminary forecast screening only. This is not an IMD warning or a flood prediction.";
    card.append(head,rationale,note);container.append(card);
  }
  if(result?.structured_answer&&typeof result.structured_answer==="object"){
    const answer=result.structured_answer;
    const sections=[
      ["Current conditions and forecast","current_conditions_and_forecast"],
      ["Historical context","historical_context"],
      ["What to watch next","what_to_watch_next"],
      ["Recommended actions","recommended_actions"],
      ["Confidence and limitations","confidence_and_limitations"]
    ];
    for(const [heading,key] of sections){
      const section=document.createElement("section");section.className="assistant-answer-section";
      const title=document.createElement("h4");title.textContent=heading;section.append(title);
      const value=answer[key];
      if(Array.isArray(value)){
        const list=document.createElement("ul");
        value.filter(item=>typeof item==="string"&&item.trim()).forEach(item=>{const li=document.createElement("li");li.innerHTML=renderInlineMarkdown(item);list.append(li)});
        section.append(list);
      }else{
        const p=document.createElement("p");p.innerHTML=renderInlineMarkdown(typeof value==="string"&&value.trim()?value:"No details were returned for this section.");section.append(p);
      }
      container.append(section);
    }
    return;
  }
  const body=document.createElement("div");body.className="assistant-markdown";body.innerHTML=renderMarkdown(reply);
  container.append(body);
}

async function sendQuestion(question){
  const input=$("#chat-input"),text=(question||input.value).trim();if(!text||state.asking)return;
  state.asking=true;
  const submit=$("#chat-form button[type=submit]");if(submit)submit.disabled=true;
  addChat("user",text);input.value="";
  const placeholder=addChat("assistant","Checking retrieved evidence…");
  const bubble=placeholder.querySelector(".chat-bubble");
  const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),70000);
  try{
    const body={question:text,district_id:state.districtId,language:getLanguage(),history:state.chatHistory.slice(-8).map(turn=>({role:turn.role,content:String(turn.content??"").slice(0,1400)}))};
    const start=$("#history-start").value,end=$("#history-end").value;if(start&&end&&end>=start){body.start=start;body.end=end}
    const result=await api("/ai/ask",{method:"POST",body:JSON.stringify(body),signal:controller.signal});
    const reply=result.available?result.answer:result.message;
    renderAssistantReply(bubble,result,typeof reply==="string"&&reply?reply:"The assistant returned no answer.");
    if(result.available){state.chatHistory.push({role:"user",content:text.slice(0,1400)},{role:"assistant",content:String(reply??"").slice(0,1400)});state.chatHistory=state.chatHistory.slice(-12)}
    $("#ai-status").textContent=result.available?`Connected · ${result.model}`:"Mistral unavailable or not configured";
  }catch(e){bubble.textContent=e.name==="AbortError"?"The request took too long. Please try again.":`I couldn't complete this request: ${e.message}`}
  finally{clearTimeout(timer);state.asking=false;if(submit)submit.disabled=false}
}
function addChat(role,message){
  const wrapper=document.createElement("div");wrapper.className=`chat-message ${role==="user"?"user-message":"assistant-message"}`;
  const avatar=document.createElement("div");avatar.className="chat-avatar";avatar.textContent=role==="user"?"TN":"✳";
  const bubble=document.createElement("div");bubble.className="chat-bubble";bubble.textContent=message;
  wrapper.append(avatar,bubble);$("#chat-messages").append(wrapper);$("#chat-messages").scrollTop=$("#chat-messages").scrollHeight;return wrapper;
}
function wireEvents(){
  $$(".nav-item[data-view]").forEach(b=>b.addEventListener("click",()=>showView(b.dataset.view)));
  $$("[data-go]").forEach(b=>b.addEventListener("click",()=>showView(b.dataset.go)));
  $("#district-select").addEventListener("change",e=>selectDistrict(e.target.value));
  $$(".district-select-sync").forEach(s=>s.addEventListener("change",e=>selectDistrict(e.target.value)));
  $("#load-overview").addEventListener("click",()=>loadOverview());
  $("#refresh-btn").addEventListener("click",()=>refreshCurrent());
  $$("[data-refresh]").forEach(b=>b.addEventListener("click",()=>refreshCurrent(true)));
  $("#load-history").addEventListener("click",loadHistory);
  $("#export-csv").addEventListener("click",exportCSV);
  $("#load-comparison").addEventListener("click",loadComparison);
  $("#district-search").addEventListener("input",e=>renderDistricts(e.target.value));
  $("#district-grid").addEventListener("click",e=>{const card=e.target.closest("[data-district-card]");if(card){selectDistrict(card.dataset.districtCard);showView("overview")}});
  $("#reload-sources").addEventListener("click",loadSources);
  $("#chat-form").addEventListener("submit",e=>{e.preventDefault();sendQuestion()});
  $$(".suggested-questions button").forEach(b=>b.addEventListener("click",()=>sendQuestion(b.dataset.question)));
  $("#mobile-menu").addEventListener("click",()=>$("#sidebar").classList.toggle("open"));
  $("#save-settings").addEventListener("click",()=>{setLanguage($("#language-select").value);applyLanguage(getLanguage());$("#language-select").value=getLanguage();selectDistrict($("#default-district").value);$("#settings-saved").textContent=t("Preferences saved in this browser.");toast(t("Preferences saved."));});
}
async function refreshCurrent(force=false){
  try{
    if(force&&state.districtId)await api(`/weather/forecast?district_id=${state.districtId}&refresh=true`);
    await loadOverview();
    if(state.lastView==="live")await loadLive();
    if(state.lastView==="forecast")await loadForecastDetail();
    toast(force?"Refresh complete.":"Dashboard updated.");
  }catch(e){toast(e.message)}
}
async function init(){
  $("#language-select").value=getLanguage();
  initLanguagePreference();
  $("#today-label").textContent=today.toLocaleDateString(getLanguage()==="ta"?"ta-IN":"en-IN",{weekday:"short",day:"numeric",month:"short",year:"numeric"});
  $("#history-start").value=daysAgo(29);$("#history-end").value=dateISO(today);
  $("#analytics-start").value=daysAgo(29);$("#analytics-end").value=dateISO(today);
  wireEvents();
  try{
    const data=await api("/districts");state.districts=data.districts;
    if(!district(state.districtId))state.districtId="chennai";
    populateDistrictSelects();initMap();renderDistricts();await loadOverview();
  }catch(e){toast(`Cannot connect to Mazhai AI API: ${e.message}`);$("#sidebar-status").textContent="API unavailable"}
  try{await api("/health")}catch{$("#sidebar-status").textContent="API unavailable"}
}
init();

"use strict";
const $ = id => document.getElementById(id);
async function loadLiveStatus(){try{const r=await fetch("/api/live/summary");const d=await r.json();if(!r.ok)throw new Error(d.error||"offline");$("live-state").textContent="CONNECTED · READ-ONLY";$("live-nodes").textContent=d.observations.nodes;$("live-pods").textContent=d.observations.pods;$("live-events").textContent=d.observations.events;const nr=await fetch("/api/live/nodes");const nodes=await nr.json();$("live-node-list").replaceChildren(...nodes.map(n=>{const el=document.createElement("article");el.className="node-card";el.innerHTML=`<span class="node-health ${n.ready?"ready":"not-ready"}"></span><div><strong>${n.name}</strong><small>${n.roles.join(" · ")||"worker"} · ${n.kubelet}</small></div><b>${n.ready?"READY":"CHECK"}</b>`;return el;}));}catch(e){$("live-state").textContent="SYNTHETIC MODE · LIVE LINK UNAVAILABLE";}}
const labels = {duplicate_ip: "Duplicate IP address", storage_capacity: "Replica scheduling capacity", container_oom: "Container memory limit", insufficient_evidence: "Insufficient evidence"};
loadLiveStatus();
const toolLabels = {inspect_node: "Read node health", read_events: "Read incident events", inspect_network: "Inspect address ownership", inspect_storage: "Inspect storage capacity", inspect_workload: "Inspect workload health", search_runbooks: "Retrieve runbook guidance"};
let cases = [], selected = null, selectedNode = null, current = null, busy = false;
function node(tag, text, className) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (className) e.className = className; return e; }
function clearResult() { current = null; $("results").hidden = true; $("empty-state").hidden = false; $("error").hidden = true; $("run-state").textContent = "READY"; $("run-state").className = "state-badge"; }
function selectCase(item) {
  if (busy) return;
  selected = item; clearResult();
  $("case-title").textContent = item.title; $("case-alert").textContent = item.alert;
  $("resource-tags").replaceChildren(...Object.entries(item.resources).map(([key,value]) => node("span", `${key}: ${value}`, "tag")));
  for (const button of $("cases").children) button.setAttribute("aria-pressed", String(button.dataset.case === item.id));
  $("investigate").disabled = false;
}
function setTab(name, focus=false) {
  for (const tab of document.querySelectorAll("[role=tab]")) { const active = tab.dataset.pane === name; tab.setAttribute("aria-selected", String(active)); tab.tabIndex = active ? 0 : -1; if (active && focus) tab.focus(); }
  for (const pane of document.querySelectorAll(".result-pane")) pane.hidden = pane.id !== `pane-${name}`;
}
function render(result) {
  current = result; $("empty-state").hidden = true; $("results").hidden = false;
  $("run-state").textContent = result.report.diagnosis === "insufficient_evidence" ? "ABSTAINED" : "REPORT READY"; $("run-state").className = "state-badge complete";
  $("diagnosis").textContent = labels[result.report.diagnosis] || result.report.diagnosis;
  $("summary").textContent = result.report.summary; $("limitations").textContent = result.report.limitations;
  const metrics = [[result.metrics.tool_calls, "TOOL CALLS"], [result.sources.length, "CITED CHUNKS"], [`${(result.metrics.duration_ms/1000).toFixed(2)}s`, "ELAPSED"], [result.is_model_inference ? result.metrics.input_tokens + result.metrics.output_tokens : "No LLM", "MODEL TOKENS"]];
  $("metrics").replaceChildren(...metrics.map(([value,label]) => {const e=node("div",undefined,"metric"); e.append(node("strong",value),node("span",label));return e;}));
  $("pane-trace").replaceChildren(...result.trace.map((step,i) => {const e=node("div",undefined,"trace-step"), details=node("details"),summary=node("summary",`${String(i+1).padStart(2,"0")}  ${toolLabels[step.tool] || step.tool}`);details.append(summary,node("pre",JSON.stringify({arguments:step.arguments,result:step.output},null,2)));e.append(details,node("small",`${step.tool} · round ${step.round} · ${step.tool === "search_runbooks" ? "local BM25 search" : "synthetic observation"}`));return e;}));
  $("pane-evidence").replaceChildren(...Object.entries(result.evidence).map(([id,data]) => {const e=node("article",undefined,"evidence-card");e.append(node("h4",id),node("pre",JSON.stringify(data,null,2)));return e;}));
  $("pane-sources").replaceChildren(...result.sources.map(source => {const e=node("article",undefined,"source-card");e.append(node("span",`${source.source} · ${source.id}`,"mini-label"),node("h4",`${source.title} / ${source.section}`),node("p",source.text.split("\n").slice(2).join("\n")));return e;}));
  $("next-steps").replaceChildren(...result.report.next_steps.map(text => node("li",text))); setTab("trace");
}
$("investigate").addEventListener("click", async () => {
  if (!selected || busy) return; busy=true; clearResult(); $("investigate").disabled=true; $("provider").disabled=true;
  $("investigate").textContent="Investigating…"; $("run-state").textContent="RUNNING";
  for(const b of $("cases").children) b.disabled=true;
  try {
    const response=await fetch("/api/investigate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({scenario_id:selected.id,provider:$("provider").value,node_name:selectedNode?.name||""})});
    const result=await response.json(); if(!response.ok) throw new Error(result.error || "Investigation failed");render(result);
  } catch(error) {$("error").textContent=error.message;$("error").hidden=false;$("run-state").textContent="NOT COMPLETED";}
  finally {busy=false;$("investigate").disabled=false;$("provider").disabled=false;$("investigate").replaceChildren(document.createTextNode(`Investigate ${selectedNode?.name||"selected node"} `),node("span","↗"));for(const b of $("cases").children)b.disabled=false;}
});
for(const tab of document.querySelectorAll("[role=tab]")) {
  tab.addEventListener("click",()=>setTab(tab.dataset.pane));
  tab.addEventListener("keydown",event=>{if(!["ArrowLeft","ArrowRight","Home","End"].includes(event.key))return;event.preventDefault();const tabs=[...document.querySelectorAll("[role=tab]")];let i=tabs.indexOf(tab);i=event.key==="Home"?0:event.key==="End"?tabs.length-1:(i+(event.key==="ArrowRight"?1:-1)+tabs.length)%tabs.length;setTab(tabs[i].dataset.pane,true);});
}
$("provider").addEventListener("change",()=>{clearResult();$("mode-note").textContent=$("provider").value==="demo"?"The demo uses a deterministic policy. It shows the workflow, not model intelligence.":"The local model chooses tools and generates the report. Evidence and citation gates still apply.";});
$("download").addEventListener("click",()=>{if(!current)return;const url=URL.createObjectURL(new Blob([JSON.stringify(current,null,2)],{type:"application/json"})),a=node("a");a.href=url;a.download=`investigation-${current.scenario_id}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
async function init(){
  const openOption=node("option","OpenAI-compatible · not configured");openOption.value="openrouter";openOption.disabled=true;$("provider").append(openOption);
  try{const [r,c]=await Promise.all([fetch("/api/scenarios"),fetch("/api/config")]);if(!r.ok||!c.ok)throw new Error("Could not load the lab");cases=await r.json();const config=await c.json();$("cases").replaceChildren(...cases.map((item,i)=>{const b=node("button",undefined,"case-button");b.type="button";b.dataset.case=item.id;b.setAttribute("aria-pressed","false");b.append(node("span",`CASE ${String(i+1).padStart(2,"0")}`,"case-number"),node("span",item.title,"case-title"),node("span",item.resources.namespace+" / "+item.resources.node,"case-sub"));b.addEventListener("click",()=>selectCase(item));return b;}));if(config.ollama_enabled){const o=$("provider").querySelector('[value="ollama"]');o.disabled=false;o.textContent=`Local LLM · ${config.model}`;$("provider").value="ollama";$("mode-note").textContent="Local LLM is the default. Evidence and citation gates remain active.";}selectCase(cases[0]);}
  catch(error){$("cases").replaceChildren(node("p","Lab unavailable. Refresh after starting the server."));$("error").textContent=error.message;$("error").hidden=false;}
}
async function loadNodeSelector(){try{const r=await fetch("/api/live/nodes");if(!r.ok)throw new Error("Live nodes unavailable");const nodes=await r.json();selectedNode=nodes[0]||null;const select=$("node-select");select.replaceChildren(...nodes.map(item=>{const o=node("option",`${item.name} · ${item.ready?"READY":"CHECK"}`);o.value=item.name;return o;}));select.disabled=!selectedNode;$("selected-node-label")?.replaceChildren(document.createTextNode(selectedNode?.name||"Select a live node"));$("investigate").replaceChildren(document.createTextNode(`Investigate ${selectedNode?.name||"selected node"} `),node("span","↗"));select.addEventListener("change",()=>{selectedNode=nodes.find(item=>item.name===select.value)||null;$("selected-node-label")?.replaceChildren(document.createTextNode(selectedNode?.name||"Select a live node"));$("investigate").replaceChildren(document.createTextNode(`Investigate ${selectedNode?.name||"selected node"} `),node("span","↗"));});}catch(error){$("node-select").replaceChildren(node("option","Live inventory unavailable"));}}
init(); loadNodeSelector();
fetch("/api/config").then(r=>r.json()).then(config=>{if(config.openrouter_enabled){const o=$("provider").querySelector('[value="openrouter"]');o.disabled=false;o.textContent=`OpenAI-compatible · ${config.openai_model||"configured"}`;}}).catch(()=>{});

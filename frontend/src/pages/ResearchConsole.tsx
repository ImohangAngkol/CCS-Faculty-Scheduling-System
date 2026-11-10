import {useEffect,useRef,useState} from "react";
import {Link,Navigate,useSearchParams} from "react-router-dom";
import {useAuth} from "../context/AuthContext";
import {accountHome} from "../services/auth";
import AccountMenu from "../components/common/AccountMenu";
import MetadataState from "../components/dashboard/MetadataState";
import ConvergenceChart from "../components/ga/ConvergenceChart";
import {researchCapabilities,researchRuns,researchDetail,researchEvents} from "../api/researchObservations";
import {authorizeCachedObservation,observationReliability,researchTime,validateObservationAdvance,mergeObservations} from "../services/researchFreshness";
import type {ResearchDetail,ResearchEvent,ResearchRun} from "../api/researchObservations";
const box="rounded-xl border border-slate-200 bg-white p-5 space-y-3";
const message="Research observations unavailable or access denied. An isolated authorized source is required. No operation was performed.";
export default function ResearchConsole(){
  const {user,status,error,refresh}=useAuth();
  if(status==="loading")return <MetadataState title="Verifying session" description="Checking your account."/>;
  if(status==="error")return <MetadataState title="Session unavailable" description={error} retry={()=>void refresh()}/>;
  if(!user)return <Navigate to="/login" replace/>;
  return <Console key={user.id}/>;
}
function Console(){
  const {user}=useAuth();const [params,setParams]=useSearchParams();
  const candidate=params.get("run");const selected=candidate&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(candidate)?candidate:undefined;
  const select=(run?:string)=>setParams(run?{run}:{},{replace:true});
  const [attempt,retry]=useState(0),[offset,setOffset]=useState(0);
  const [view,setView]=useState<{offset:number;items:ResearchRun[];next:number|null;error?:string;denied?:boolean}>();
  const key=String(offset),requestKey=`${offset}:${attempt}`;
  useEffect(()=>{const abort=new AbortController();void(async()=>{try{await researchCapabilities(abort.signal);const rows=await researchRuns(offset,abort.signal);if(!abort.signal.aborted)setView({offset,items:rows.items,next:rows.next_offset});}catch(error){if(!abort.signal.aborted)setView(old=>authorizeCachedObservation(error)&&old?.offset===offset?{...old,error:message}:{offset,items:[],next:null,error:message,denied:!authorizeCachedObservation(error)});}})();return()=>abort.abort();},[offset,requestKey]);
  const current=view?.offset===offset?view:undefined;
  return <div className="min-h-screen bg-slate-50"><AccountMenu/><main className="mx-auto max-w-6xl space-y-5 p-4 sm:p-8">
    <header className="rounded-xl border border-teal-200 bg-teal-50 p-5 space-y-2"><h1 className="text-2xl font-bold text-teal-950">Isolated research console</h1><p>Read-only fictional GA research. Not institutional authorization or publication.</p><p className="font-semibold text-amber-900">Production admission and Saved Best promotion: BLOCKED | Continuous Optimization: DISABLED | Active restore: BLOCKED | Seven-day readiness: NO-GO</p><Link to={accountHome(user!)} className="text-teal-800 underline">Return to dashboard</Link></header>
    <section className={box}><h2 className="text-lg font-bold text-teal-900">Research run history</h2><button className="ccs-btn-secondary" onClick={()=>retry(n=>n+1)}>Refresh run history</button>
      {!current?<MetadataState title="Loading research observations" description="Checking scoped read access."/>:<>{current.error&&<MetadataState title="Research source unavailable" description={current.error+(current.items.length?" Previously retrieved run history retained.":"")} retry={()=>retry(n=>n+1)}/>}{!current.error&&!current.items.length&&<p role="status">No research runs in your authorized scope.</p>}<ul className="space-y-2">{current.items.map(r=><li key={r.run_id}><button className="w-full break-all rounded-lg border p-3 text-left hover:border-teal-600" aria-pressed={selected===r.run_id} onClick={()=>select(r.run_id)}>{r.run_id} | {r.state} | Best penalty: {r.best_so_far_fitness===null?"Unavailable":String(r.best_so_far_fitness)}</button></li>)}</ul></>}
      <div className="flex gap-3"><button className="ccs-btn-secondary" disabled={!offset} onClick={()=>{select(undefined);setOffset(n=>Math.max(0,n-10));}}>Previous runs</button><button className="ccs-btn-secondary" disabled={!current?.next} onClick={()=>{select(undefined);setOffset(current!.next!);}}>More runs</button></div>
    </section>
    {selected&&current&&!current.denied&&<Detail key={`${selected}:${key}`} run={selected}/>}
  </main></div>;
}
function Reliability({run,aged}:{run:ResearchRun;aged:boolean}){
  const f=observationReliability(run,aged?33000:0);
  return <aside className="rounded border border-amber-200 bg-amber-50 p-4" aria-label="Observation reliability"><h3 className="font-semibold">Observation freshness: {f.state}</h3><p>{f.reason}</p>{"freshness" in run&&<p>Telemetry age classification: {run.freshness.telemetry_state}; supported threshold: 30 seconds.</p>}<p>Last verified observation (server source time): {researchTime(f.lastVerified)}</p><p>Snapshot verified at (server clock): {researchTime(f.serverVerified)}</p>{f.state==="STALE"&&<p role="status">Stale telemetry. No recent persisted update; worker termination is not inferred.</p>}{f.state==="UNKNOWN"&&<p role="status">Observation freshness or ownership is unknown. No worker health or completion is inferred.</p>}{f.state==="TERMINAL"&&<p>Confirmed durable terminal outcome at this snapshot; historical telemetry is not a live heartbeat.</p>}<p>HTTP success verifies retrieval only. Worker health is not established by this connection.</p></aside>;
}
function Detail({run}:{run:string}){
  const [attempt,retry]=useState(0),[view,setView]=useState<{data?:ResearchDetail;retrievedAt:string;received:number;error?:string;retrying?:boolean}>();
  const [extra,setExtra]=useState<ResearchEvent[]>([]),[aged,age]=useState(false);
  const pending=useRef<AbortController|null>(null),last=useRef<ResearchDetail|undefined>(undefined);
  function refresh(){pending.current?.abort();setView(v=>v?{...v,retrying:true}:v);retry(n=>n+1);}
  useEffect(()=>{const abort=new AbortController();pending.current=abort;let timer:ReturnType<typeof setTimeout>|undefined;let polls=0;
    const load=async()=>{try{const data=validateObservationAdvance(last.current,await researchDetail(run,abort.signal));if(abort.signal.aborted)return;last.current=data;age(false);setView({data,retrievedAt:new Date().toISOString(),received:performance.now()});
      if(["RUNNING","RESUMING","PAUSING","STOPPING"].includes(data.overview.state)&&polls++<6)timer=setTimeout(()=>void load(),10000);
    }catch(error){if(!abort.signal.aborted){const retain=authorizeCachedObservation(error);if(!retain){last.current=undefined;setExtra([]);}setView(old=>({data:retain?old?.data:undefined,retrievedAt:old?.retrievedAt??"Unavailable",received:old?.received??0,error:retain?message:"Verification or access rejected. Cached observations cleared."}));}}};
    void load();return()=>{abort.abort();if(timer)clearTimeout(timer);};
  },[run,attempt]);
  const data=view?.data,received=view?.received;
  useEffect(()=>{if(!data||!('freshness' in data.overview)||data.overview.freshness.state!=="FRESH"||received===undefined)return;
    const f=data.overview.freshness;const delay=Math.max(1,(f.threshold_seconds-f.age_seconds!)*1000-(performance.now()-received)+1);
    const timer=setTimeout(()=>age(true),delay);return()=>clearTimeout(timer);
  },[data,received]);
  if(!view)return <MetadataState title="Loading selected run" description="Reading durable observations."/>;
  if(!data)return <MetadataState title="Run observations unavailable" description={view.error??message} retry={refresh}/>;
  const detail=data.overview,events=mergeObservations(data.telemetry.items,extra),next=events.length<data.telemetry.total?(events.at(-1)?.sequence??0):null;
  return <section className={box} aria-label="Selected research run"><h2 className="text-xl font-bold text-teal-900">Run overview</h2><p className="break-all">{run}</p><p>State: <strong>{detail.state}</strong> ({detail.state_classification.toLowerCase()}) | Worker record: {detail.worker_state}</p><p>Termination/interruption reason: {detail.reason??"Unavailable / not recorded"}</p><p>Generation: {detail.generation??"Unavailable"} | Best-so-far penalty: <strong>{detail.best_so_far_fitness===null?"Unavailable":String(detail.best_so_far_fitness)}</strong></p><p>Current fitness: unavailable (not exposed). Satisfaction metrics: unavailable (not emitted).</p>
    <button className="ccs-btn-secondary" onClick={refresh}>Refresh selected observations</button><p className="text-sm text-slate-600">Active runs receive at most six automatic refreshes, ten seconds apart. Reads stop on error, terminal state or navigation.</p>
    <Reliability run={detail} aged={aged}/><p>Last successful retrieval (browser clock): {view!.retrievedAt}</p>
    {view!.error&&<MetadataState title="Run observations unavailable" description={view!.error+" Historical observations retained; connection success is not worker health."} retry={refresh}/>}
    {view!.retrying&&<p role="status">Retrying read; historical observations retained.</p>}
    <div className="rounded border border-teal-200 bg-teal-50 p-4"><h3 className="font-semibold">Trusted context summary</h3><p>{detail.context_qualification}</p><p>{data.provenance.context.academic_year} | {data.provenance.context.term} | {data.provenance.context.dataset_identity}</p><dl className="space-y-1 text-xs">{Object.entries(data.provenance.context).map(([k,v])=><div key={k} className="break-all"><dt className="inline font-semibold">{k}: </dt><dd className="inline">{v}</dd></div>)}</dl><p className="break-all text-xs">Context identity: {detail.context_id}</p><p>Technical fictional input verification does not establish institutional approval.</p></div>
    <h3 className="font-semibold">Recorded fitness history</h3>{data.fitness.availability==="OBSERVED"?<><ConvergenceChart key={run} history={data.fitness.points.map(p=>({...p,input_fingerprint:detail.context_id,configuration_fingerprint:data.provenance.configuration_fingerprint}))}/><table className="w-full text-left text-sm"><caption>Exact recorded best-ever penalties; lower is better.</caption><thead><tr><th>Generation</th><th>Best-ever penalty</th></tr></thead><tbody>{data.fitness.points.map(p=><tr key={p.generation}><td>{p.generation}</td><td>{String(p.best_ever_fitness)}</td></tr>)}</tbody></table></>:<p role="status">Generation-level fitness history unavailable: no verified history was recorded.</p>}
    <h3 className="font-semibold">Execution timeline</h3><p className="text-sm">{data.observation_notice}</p><ol className="space-y-2">{events.map(e=><li className="rounded border p-3 text-sm" key={e.sequence}>#{e.sequence} | {e.worker_state??e.recovery_state??"Recorded observation"} | {researchTime(e.observed_at)}<p>{e.exit_reason??e.reason??"No reason recorded"}</p><p>Generation {e.generation??"unavailable"} | Best {e.best_so_far_fitness===null||e.best_so_far_fitness===undefined?"unavailable":String(e.best_so_far_fitness)}</p><p>{e.generation_and_best_classification??e.classification??"Unavailable"}</p></li>)}</ol>{!events.length&&<p>No persisted telemetry is available.</p>}
    {next!==null&&<MoreEvents key={`${run}:${next}`} run={run} after={next} context={detail.context_id} onPage={page=>setExtra(mergeObservations(extra,page.items))}/>}
    <h3 className="font-semibold">Checkpoint metadata</h3><p>Sequence {detail.checkpoint_sequence} | Active restoration unavailable.</p><p className="break-all text-xs">{detail.checkpoint_fingerprint??"No checkpoint recorded"}</p>
  </section>;
}
function MoreEvents({run,after,context,onPage}:{run:string;after:number;context:string;onPage:(page:Awaited<ReturnType<typeof researchEvents>>)=>void}){
  const pending=useRef<AbortController|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState("");
  useEffect(()=>()=>{pending.current?.abort();},[]);
  async function load(){
    pending.current?.abort();const c=new AbortController();pending.current=c;setBusy(true);setError("");
    try{const page=await researchEvents(run,after,context,c.signal);if(!c.signal.aborted)onPage(page);}
    catch{if(!c.signal.aborted)setError(message);}
    finally{if(!c.signal.aborted)setBusy(false);}
  }
  return <><button className="ccs-btn-secondary" disabled={busy} onClick={()=>void load()}>More observations</button>{error&&<p role="alert">{error}</p>}</>;
}

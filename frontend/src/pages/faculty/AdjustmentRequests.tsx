import {useEffect,useRef,useState} from "react";
import {Link} from "react-router-dom";
import {useAuth} from "../../context/AuthContext";
import MetadataState from "../../components/dashboard/MetadataState";
import {adjustmentError as metadataError,createAdjustment,getAdjustment,getAdjustmentAssignments,listAdjustments,previewAdjustment,transitionAdjustment} from "../../api/adjustments";
import type {AdjustmentInput,AdjustmentRecord,AdjustmentReview,AssignmentBundle} from "../../api/adjustments";

const box="min-w-0 rounded-xl border border-slate-200 bg-white p-5 space-y-3";
const field="block w-full rounded-lg border border-slate-300 p-2";
function Findings({review}:{review:AdjustmentReview}) {return <div role="status" className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm"><p className="font-semibold">{review.validation.outcome==="VALID_PROPOSAL"?"Valid proposal within checked constraints":"Proposal requires authorized review"}</p>{review.validation.findings.map(f=><p key={f.code}>{f.code}: {f.message}</p>)}<p>No approval or schedule change has occurred.</p></div>;}

export default function AdjustmentRequests() {
  const {user}=useAuth();
  // Remount on account changes so another principal never inherits private UI state.
  return <Requests key={`${user?.id}:${user?.faculty?.faculty_id}`} bound={Boolean(user?.faculty)}/>;
}

function Requests({bound}:{bound:boolean}) {
  const [attempt,setAttempt]=useState(0),[loading,setLoading]=useState(bound);
  const [bundle,setBundle]=useState<AssignmentBundle>(),[rows,setRows]=useState<AdjustmentRecord[]>([]),[cursor,setCursor]=useState<string|null>(null);
  const [sourceError,setSourceError]=useState(""),[listError,setListError]=useState(""),[error,setError]=useState(""),[notice,setNotice]=useState("");
  const [selected,setSelected]=useState(""),[day,setDay]=useState<AdjustmentInput["proposal"]["day"]>("M"),[start,setStart]=useState(""),[end,setEnd]=useState(""),[room,setRoom]=useState(""),[reason,setReason]=useState("");
  const [review,setReview]=useState<AdjustmentReview>(),[detail,setDetail]=useState<AdjustmentRecord>(),[confirm,setConfirm]=useState(false),[busy,setBusy]=useState(false);
  const createOperation=useRef(crypto.randomUUID()),operations=useRef(new Map<string,string>());
  useEffect(()=>{
    if(!bound)return;
    const controller=new AbortController();
    Promise.allSettled([getAdjustmentAssignments(controller.signal),listAdjustments(controller.signal)]).then(([a,b])=>{
      if(controller.signal.aborted)return;
      if(a.status==="fulfilled")setBundle(a.value);else setSourceError(metadataError(a.reason,"Verified assignments are unavailable. My Schedule remains read only."));
      if(b.status==="fulfilled"){setRows(b.value.items);setCursor(b.value.next_cursor);}else setListError(metadataError(b.reason,"Request history is unavailable. Retry before creating another request."));
      setLoading(false);
    });
    return()=>controller.abort();
  },[bound,attempt]);
  const reload=()=>{setLoading(true);setBundle(undefined);setSourceError("");setListError("");setReview(undefined);setSelected("");setAttempt(a=>a+1);};
  const original=bundle?.assignments.find(m=>m.id===selected);
  const changed=()=>{setReview(undefined);setNotice("");setError("");createOperation.current=crypto.randomUUID();};
  const choose=(id:string)=>{const m=bundle?.assignments.find(a=>a.id===id);setSelected(id);setDay((m?.day??"M") as typeof day);setStart(m?.start??"");setEnd(m?.end??"");setRoom(m?.room_id??"");setReason("");changed();};
  const body=():AdjustmentInput=>{
    if(!bundle||!original)throw new Error("Select one of your current assignments.");
    return {schedule_id:bundle.schedule_id,revision:bundle.revision,assignment_id:original.id,academic_year:bundle.academic_year,term:bundle.term,proposal:{day,start,end,room_id:room},justification:reason};
  };
  const run=async(action:()=>Promise<void>)=>{setBusy(true);setError("");setNotice("");try{await action();}catch(e){setError(metadataError(e,"The operation could not be verified. Reload request status before retrying."));}finally{setBusy(false);}};
  const merge=(value:AdjustmentRecord)=>{setDetail(value);setRows(items=>[value,...items.filter(i=>i.id!==value.id)]);setConfirm(false);};
  const transition=(action:"submit"|"withdraw")=>run(async()=>{
    if(!detail)return;const key=`${detail.id}:${detail.version}:${action}`;
    if(!operations.current.has(key))operations.current.set(key,crypto.randomUUID());
    merge(await transitionAdjustment(detail,action,operations.current.get(key)!));
    setNotice(action==="submit"?"Request submitted. Awaiting a future Department Chair workflow; your schedule is unchanged.":"Request withdrawn. Its history is retained; your schedule is unchanged.");
  });
  return <div className="min-w-0 space-y-6">
    <header className="rounded-xl border border-teal-200 bg-teal-50 p-5"><h1 className="text-2xl font-bold text-teal-950">Schedule Adjustment Requests</h1><p className="mt-2">Propose changes to your own GA-generated assignments.</p><p className="mt-2 font-semibold">Requests are proposals. Department Chair decisions are not implemented in D11. Your teaching schedule remains unchanged.</p><Link className="text-teal-800 underline" to="/faculty/schedule">View My Schedule</Link></header>
    {!bound&&<MetadataState title="Faculty binding unavailable" description="Ask an administrator to verify your account binding. No faculty identity is selected."/>}
    {loading&&<MetadataState title="Loading adjustment requests" description="Retrieving your verified assignments and private request history."/>}
    {sourceError&&<MetadataState title="Adjustment source unavailable" description={sourceError} retry={reload}/>}
    {error&&<p role="alert" className="rounded-lg bg-red-50 p-4 text-red-900">{error}</p>}
    {notice&&<p role="status" className="rounded-lg bg-teal-50 p-4 text-teal-950">{notice}</p>}
    {bundle&&<section className={box} aria-label="Current assignments"><h2 className="text-lg font-bold text-teal-900">Your current assignments</h2><p>{bundle.academic_year} · {bundle.term}</p><p className="break-all text-xs">Schedule revision: {bundle.revision}</p>
      {!bundle.assignments.length?<p>No eligible assignments in this proposal.</p>:<label>Assignment<select className={field} aria-label="Adjustment assignment" value={selected} disabled={busy} onChange={e=>choose(e.target.value)}><option value="">Select an assignment</option>{bundle.assignments.map(m=><option key={m.id} value={m.id}>{m.subject} · {m.section} · {m.component} · {m.day} {m.start}–{m.end}</option>)}</select></label>}
      {original&&<form className="space-y-4" onSubmit={e=>{e.preventDefault();void run(async()=>setReview(await previewAdjustment(body())));}}>
        <div className="rounded-lg bg-slate-50 p-3"><h3 className="font-semibold">Original assignment</h3><p>{original.subject} — {original.title}</p><p>{original.section} · {original.component} · {original.day} {original.start}–{original.end} · {bundle.rooms.find(r=>r.id===original.room_id)?.name}</p><p className="text-sm">Keep this meeting's duration. Linked lecture/laboratory meetings remain unchanged.</p></div>
        <fieldset disabled={busy} className="grid gap-3 sm:grid-cols-2"><legend className="mb-2 font-semibold">Proposed meeting</legend>
          <label>Day<select className={field} aria-label="Proposed day" value={day} onChange={e=>{setDay(e.target.value as typeof day);changed();}}>{["M","T","W","TH","F","S"].map(d=><option key={d}>{d}</option>)}</select></label>
          <label>Room<select className={field} aria-label="Proposed room" value={room} onChange={e=>{setRoom(e.target.value);changed();}}>{bundle.rooms.filter(r=>r.kind===original.component).map(r=><option value={r.id} key={r.id}>{r.name}</option>)}</select></label>
          <label>Start time<input required type="time" step="1800" aria-label="Proposed start" className={field} value={start} onChange={e=>{setStart(e.target.value);changed();}}/></label>
          <label>End time<input required type="time" step="1800" aria-label="Proposed end" className={field} value={end} onChange={e=>{setEnd(e.target.value);changed();}}/></label>
          <label className="sm:col-span-2">Justification<textarea required minLength={10} maxLength={2000} aria-label="Adjustment justification" className={field} value={reason} onChange={e=>{setReason(e.target.value);changed();}}/></label>
        </fieldset>
        <button className="ccs-btn-secondary" disabled={busy} type="submit">Validate proposal</button>
        {review&&<><Findings review={review}/><button type="button" className="ccs-btn-primary" disabled={busy||Boolean(listError)} onClick={()=>void run(async()=>{merge(await createAdjustment(body(),createOperation.current));setNotice("Draft created. Review its immutable details before submission.");})}>Save draft request</button></>}
      </form>}
    </section>}
    <section className={box} aria-label="My request history"><h2 className="text-lg font-bold text-teal-900">My requests</h2>{listError?<MetadataState title="Request history unavailable" description={listError} retry={reload}/>:!loading&&!rows.length?<p>No adjustment requests yet.</p>:rows.map(r=><button className="block w-full rounded-lg border border-slate-200 p-3 text-left hover:border-teal-600" key={r.id} disabled={busy} onClick={()=>void run(async()=>merge(await getAdjustment(r.id)))}><strong>{r.content.review.original.subject} · {r.content.review.original.section}</strong> <span className="ml-2 inline-block rounded-full bg-teal-50 px-2 py-1 text-xs font-semibold text-teal-900">{r.status}</span><p>{r.freshness.state} · {r.content.review.original.day} {r.content.review.original.start} → {r.content.input.proposal.day} {r.content.input.proposal.start}</p></button>)}
      {cursor&&<button className="ccs-btn-secondary" disabled={busy} onClick={()=>void run(async()=>{const page=await listAdjustments(undefined,cursor);setRows(old=>[...old,...page.items.filter(r=>!old.some(o=>o.id===r.id))]);setCursor(page.next_cursor);})}>Load more requests</button>}
    </section>
    {detail&&<section className={box} aria-label="Request details"><h2 className="text-lg font-bold text-teal-900">Request details</h2><p className="break-all text-sm">Request {detail.id} · version {detail.version} · {detail.status}</p><p>Source: {detail.freshness.state}{detail.freshness.code&&` — ${detail.freshness.code}`}</p><p>{detail.content.input.academic_year} · {detail.content.input.term}</p><p>Original: {detail.content.review.original.day} {detail.content.review.original.start}–{detail.content.review.original.end} · {detail.content.review.original.room_id}</p><p>Proposed: {detail.content.input.proposal.day} {detail.content.input.proposal.start}–{detail.content.input.proposal.end} · {detail.content.input.proposal.room_id}</p><p className="whitespace-pre-wrap break-words">Justification: {detail.content.input.justification}</p><Findings review={detail.content.review}/>
      {detail.freshness.validation&&<Findings review={{...detail.content.review,validation:detail.freshness.validation}}/>}
      <p className="break-all text-xs">Original revision: {detail.content.input.revision}<br/>Pinned GEC constraints: {detail.content.review.constraint_digest}</p>
      {detail.status==="DRAFT"&&detail.freshness.state==="CURRENT"&&!confirm&&<button disabled={busy} className="ccs-btn-primary" onClick={()=>setConfirm(true)}>Submit for future Chair review</button>}
      {confirm&&<div role="alert" className="rounded-lg bg-amber-50 p-3"><p>Submit this proposal? Its contents cannot be edited, and no schedule change or approval will occur.</p><button disabled={busy} className="ccs-btn-primary" onClick={()=>void transition("submit")}>Confirm submission</button><button disabled={busy} className="ccs-btn-secondary" onClick={()=>setConfirm(false)}>Cancel</button></div>}
      {detail.status!=="WITHDRAWN"&&<button disabled={busy} className="ccs-btn-secondary" onClick={()=>void transition("withdraw")}>Withdraw request</button>}
      <button disabled={busy} className="ccs-btn-secondary" onClick={()=>void run(async()=>merge(await getAdjustment(detail.id)))}>Refresh request status</button>
      <h3 className="font-semibold">Immutable request history</h3><ol className="space-y-2">{detail.history.map(e=><li key={e.sequence} className="break-words text-sm">{e.sequence}. {e.action} · <time>{e.created_at}</time>{e.validation&&` · ${e.validation.outcome}`}</li>)}</ol>
    </section>}
  </div>;
}

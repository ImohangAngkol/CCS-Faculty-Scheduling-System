import {useEffect,useRef,useState} from "react";
import {Link,Navigate} from "react-router-dom";
import {useAuth} from "../../context/AuthContext";
import {accountHome} from "../../services/auth";
import AccountMenu from "../../components/common/AccountMenu";
import MetadataState from "../../components/dashboard/MetadataState";
import {chairError,decideChair,getChairAccess,getChairQueue,getChairReview} from "../../api/chairReviews";
import type {ChairAccess,ChairQueue,ChairReview} from "../../api/chairReviews";

const box="rounded-xl border border-slate-200 bg-white p-5 space-y-3 min-w-0";
export default function ChairRequests(){
  const {user,status,refresh,error}=useAuth();
  if(status==="loading")return <MetadataState title="Verifying session" description="Checking your authenticated account."/>;
  if(status==="error")return <MetadataState title="Session unavailable" description={error} retry={()=>void refresh()}/>;
  if(!user)return <Navigate to="/login" replace/>;
  return <Reviews key={user.id}/>;
}

function Reviews(){
  const {user}=useAuth();
  const [access,setAccess]=useState<ChairAccess>(),[queue,setQueue]=useState<ChairQueue>(),[detail,setDetail]=useState<ChairReview>();
  const [department,setDepartment]=useState(""),[decided,setDecided]=useState(false),[attempt,setAttempt]=useState(0);
  const [loading,setLoading]=useState(true),[error,setError]=useState(""),[busy,setBusy]=useState(false),[notice,setNotice]=useState("");
  const [explanation,setExplanation]=useState(""),[confirm,setConfirm]=useState<"approve"|"reject">();
  const operations=useRef(new Map<string,string>());
  useEffect(()=>{const controller=new AbortController();
    void (async()=>{try{const grant=await getChairAccess(controller.signal);if(controller.signal.aborted)return;setAccess(grant);const rows=await getChairQueue(department,decided,controller.signal);if(!controller.signal.aborted)setQueue(rows);}catch(e){if(!controller.signal.aborted){setAccess(undefined);setQueue(undefined);setDetail(undefined);setError(chairError(e,"Chair review is unavailable. No authority has been granted."));}}finally{if(!controller.signal.aborted)setLoading(false);}})();return()=>controller.abort();
  },[department,decided,attempt]);
  const filterChanged=()=>{setQueue(undefined);setDetail(undefined);setConfirm(undefined);setError("");setNotice("");setLoading(true);};
  const reload=()=>{setLoading(true);setError("");setDetail(undefined);setConfirm(undefined);setQueue(undefined);setAttempt(a=>a+1);};
  const run=async(work:()=>Promise<void>)=>{setBusy(true);setError("");try{await work();}catch(e){setConfirm(undefined);setDetail(undefined);setError(chairError(e,"Decision could not be verified. Reload before retrying."));}finally{setBusy(false);}};
  const open=async(id:string)=>{setDetail(await getChairReview(id));setExplanation("");setConfirm(undefined);setNotice("");};
  const decide=()=>run(async()=>{if(!detail||!confirm)return;const key=JSON.stringify([detail.request.id,detail.request.version,confirm,explanation]);if(!operations.current.has(key))operations.current.set(key,crypto.randomUUID());await decideChair(detail,confirm,explanation,operations.current.get(key)!);const id=detail.request.id;await open(id);setNotice("Final decision recorded. The teaching schedule is unchanged.");setQueue(await getChairQueue(department,decided));});
  return <div className="min-h-screen bg-slate-50"><AccountMenu/><main className="mx-auto max-w-6xl space-y-5 p-4 sm:p-8">
    <header className="rounded-xl border border-teal-200 bg-teal-50 p-5"><h1 className="text-2xl font-bold text-teal-950">Department Chair request reviews</h1><p className="mt-2 font-semibold">Approval is authorization only. Approved requests remain pending application; no schedule is changed or regenerated.</p><Link className="text-teal-800 underline" to={accountHome(user!)}>Return to dashboard</Link></header>
    {loading&&<MetadataState title="Loading Chair review queue" description="Verifying your current mandate and department scope."/>}
    {error&&<MetadataState title="Chair review unavailable" description={error} retry={reload}/>}
    {notice&&<p role="status" className="rounded-lg bg-teal-50 p-4">{notice}</p>}
    {access&&<section className={box}><h2 className="text-lg font-bold text-teal-900">Department-scoped queue</h2><label>Department<select aria-label="Review department" className="ml-2 rounded border p-2" value={department} disabled={busy} onChange={e=>{setDepartment(e.target.value);filterChanged();}}><option value="">All authorized departments</option>{access.departments.map(d=><option key={d.id} value={d.id}>{d.label}</option>)}</select></label><label className="block"><input type="checkbox" checked={decided} disabled={busy} onChange={e=>{setDecided(e.target.checked);filterChanged();}}/> Include final decisions</label>
      {!loading&&queue&&!queue.items.length&&<p>No eligible requests in this verified department scope.</p>}
      {!loading&&queue?.items.map(r=><button key={r.id} className="block w-full rounded-lg border p-3 text-left hover:border-teal-600" disabled={busy} onClick={()=>void run(()=>open(r.id))}><strong>{r.subject} / {r.section}</strong> <span className="break-all">{r.status}</span><p className="break-all text-sm">Faculty {r.faculty_id} | Submitted {r.submitted_at}</p></button>)}
      <button className="ccs-btn-secondary" disabled={busy} onClick={reload}>Refresh queue</button>
    </section>}
    {detail&&<section className={box} aria-label="Chair request details"><h2 className="break-words text-xl font-bold text-teal-900 [overflow-wrap:anywhere]">Request review: {detail.request.status}</h2><p className="break-all text-sm">Faculty {detail.faculty_id} | Request {detail.request.id} | Version {detail.request.version}</p><p>{detail.request.content.input.academic_year} | {detail.request.content.input.term}</p><p>{detail.request.content.review.original.subject} / {detail.request.content.review.original.section} / {detail.request.content.review.original.component}</p>
      <p>Original: {detail.request.content.review.original.day} {detail.request.content.review.original.start}-{detail.request.content.review.original.end} / {detail.request.content.review.original.room_id}</p><p>Proposed: {detail.request.content.input.proposal.day} {detail.request.content.input.proposal.start}-{detail.request.content.input.proposal.end} / {detail.request.content.input.proposal.room_id}</p><p className="whitespace-pre-wrap break-words">Justification: {detail.request.content.input.justification}</p>
      <p className="break-all text-xs">Schedule revision: {detail.request.content.input.revision}<br/>Pinned GEC constraints: {detail.request.content.review.constraint_digest}</p>
      {detail.approval_block&&<p role="alert" className="rounded bg-amber-50 p-3">Approval blocked: {detail.approval_block.code}: {detail.approval_block.message}</p>}
      {detail.current_review&&<div role="status"><h3 className="font-semibold">Current scheduling validation</h3><p>{detail.current_review.validation.outcome}</p>{detail.current_review.validation.findings.map(f=><p key={f.code}>{f.code}: {f.message}</p>)}<p>Scheduling findings cover faculty, room, section and lecture/laboratory rules. Approval additionally requires fresh confirmed GEC applicability and institutional authority.</p></div>}
      {(detail.can_approve||detail.can_reject)&&<><label className="block">Decision explanation<textarea aria-label="Decision explanation" minLength={10} maxLength={2000} className="block w-full rounded border p-2" value={explanation} disabled={busy} onChange={e=>{setExplanation(e.target.value);setConfirm(undefined);}}/></label><div className="flex flex-wrap gap-3">{detail.can_approve&&<button className="ccs-btn-primary" disabled={busy||explanation.trim().length<10} onClick={()=>setConfirm("approve")}>Approve pending application</button>}{detail.can_reject&&<button className="ccs-btn-secondary" disabled={busy||explanation.trim().length<10} onClick={()=>setConfirm("reject")}>Reject request</button>}</div></>}
      {confirm&&<div role="alertdialog" aria-label="Confirm Chair decision" className="rounded-lg border border-amber-300 bg-amber-50 p-4"><p>Confirm {confirm}? This is a final decision and cannot be replaced. The teaching schedule will remain unchanged.</p><button className="ccs-btn-primary" disabled={busy} onClick={()=>void decide()}>Confirm decision</button><button className="ccs-btn-secondary" disabled={busy} onClick={()=>setConfirm(undefined)}>Cancel</button></div>}
      <h3 className="font-semibold">Decision history</h3>{!detail.decision_history.length&&<p>No final decision recorded.</p>}{detail.decision_history.map(d=><div className="rounded-lg bg-teal-50 p-3" key={d.id}><p>{d.status} | <time>{d.decided_at}</time></p><p className="whitespace-pre-wrap break-words">{d.explanation}</p><p className="break-all text-xs">Authorized actor: {d.actor_id}<br/>Department: {d.department_id}<br/>Audit digest: {d.payload_digest}<br/>Trust at decision: {d.provenance.trust_status}</p><p>Historical decision; current institutional trust is not implied. Teaching schedule unchanged.</p></div>)}
      <h3 className="font-semibold">Original faculty request history</h3><ol>{detail.request.history.map(e=><li key={e.sequence}>{e.sequence}. {e.action} | {e.created_at}</li>)}</ol>
      <button className="ccs-btn-secondary" disabled={busy} onClick={()=>void run(()=>open(detail.request.id))}>Refresh review</button>
    </section>}
  </main></div>;
}

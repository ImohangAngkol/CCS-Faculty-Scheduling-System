"""Read-only, candidate-bound analysis. No scoring, reconstruction or writes."""
import hashlib
import importlib
import math
import re
from collections import defaultdict

from services import ga_history_service as history, fitness_reporting_service as reporting

DAYS=("monday","tuesday","wednesday","thursday","friday","saturday")
KEYS=("subject","day","time")
KINDS=("generation_best","best_ever")
VIOLATIONS=("conflicts","eligibility_violations","overload_violations","fixed_schedule_violations","preassignment_violations","component_duration_violations")


def reject(message,code="GA_ADVANCED_INVALID",status=422):raise history.HistoryError(message,code,status)
def sha(value):return hashlib.sha256(history.checkpoints.canonical(value)).hexdigest()
def number(value):return type(value) in (int,float) and math.isfinite(value)


def minute(value):
    match=re.fullmatch(r"(\d{1,2}):(\d{2})",str(value))
    if not match or int(match[1])>23 or int(match[2])>59:reject("A recorded meeting has an invalid time.")
    return int(match[1])*60+int(match[2])


def day(value):
    aliases=dict(zip(("M","T","W","TH","F","S"),DAYS))
    text=str(value).strip();normalized=aliases.get(text.upper(),text.lower())
    normalized=next((d for d in DAYS if d==normalized or d[:3]==normalized),normalized)
    if normalized not in DAYS:reject("A recorded meeting has an unsupported day.")
    return normalized


def meeting_hours(rows):
    intervals=defaultdict(list)
    for row in rows:
        start,end=minute(row["start"]),minute(row["end"])
        if start>=end:reject("A recorded meeting has an invalid interval.")
        intervals[day(row["day"])].append((start,end))
    result={d:0.0 for d in DAYS}
    for d,spans in intervals.items():
        merged=[]
        for start,end in sorted(spans):
            if merged and start<=merged[-1][1]:merged[-1][1]=max(merged[-1][1],end)
            else:merged.append([start,end])
        result[d]=sum(end-start for start,end in merged)/60
    return result


def index(run_id):
    result=history.manifest(run_id)
    if result["run_id"]!=run_id or len(result["generations"])>10001:reject("Unsupported recorded run.")
    return result


def runs(offset=0):
    items=[];issues=[]
    if history.SNAPSHOTS_DIR.exists():
        paths=sorted(p for p in history.SNAPSHOTS_DIR.iterdir() if p.is_dir())
        if len(paths)>200:reject("More than 200 run directories require a separately scoped archive review.",status=409)
        for path in paths:
            try:
                value=index(path.name)
                items.append({"run_id":value["run_id"],"state":value["state"],"created_at":value["created_at"],"generations":len(value["generations"])})
            except history.HistoryError:issues.append("UNREADABLE_RUN_INDEX")
    items.sort(key=lambda x:(x["created_at"],x["run_id"]),reverse=True)
    return {"schema_version":1,"items":items[offset:offset+20],"offset":offset,"total":len(items),"issues":issues}


def receipt_status(run_id,data,run):
    try:module=importlib.import_module("services.ga_input_receipt")
    except ModuleNotFoundError as exc:
        if exc.name!="services.ga_input_receipt":raise
        return {"status":"UNAVAILABLE","record_state":"NOT_INSTALLED","reasons":["U5D_NOT_INSTALLED"]}
    try:
        value=module.read(run_id)
        if value["verification_status"]!="UNVERIFIED" or value["eligible_for_current"] is not False:raise ValueError()
        start=value.get("start")
        if start and (start["dataset_fingerprint"]!=data["metrics"]["input_fingerprint"] or start["run_started_at"]!=run.get("started_at")
            or start["configuration"]!=data["ga_configuration"]):
            return {"status":"UNVERIFIED","record_state":"INCOMPATIBLE_CAPTURE","reasons":["RECEIPT_HISTORY_BINDING_MISMATCH"]}
        return {"status":"UNVERIFIED","record_state":value["record_state"],"reasons":value["reasons"]}
    except (history.HistoryError,ValueError,KeyError,TypeError):return {"status":"UNVERIFIED","record_state":"INVALID","reasons":["RECEIPT_UNREADABLE_OR_INVALID"]}


def context_for(data,selected):
    context=data.get("reporting_context")
    if context is None:
        path=history.directory(data["run_id"])/f"analysis-{selected['chromosome_id']}.json"
        if path.exists():context=history.read_document(path).get("reporting_context")
    if context is not None and context.get("input_fingerprint")!=data["metrics"]["input_fingerprint"]:reject("Captured preference context uses different inputs.")
    return context


def aggregate(faculty):
    result={}
    for key in KEYS:
        applicable=[row for row in faculty if row["satisfaction"][key] is not None]
        result[key]={"value":sum(r["satisfaction"][key] for r in applicable)/len(applicable) if applicable else None,
            "count":len(applicable),"total":len(faculty),"contributors":[r["faculty"] for r in applicable]}
    complete=[r for r in faculty if all(r["satisfaction"][k] is not None for k in KEYS)]
    result["overall"]={"value":sum(sum(r["satisfaction"][k] for k in KEYS)/3 for r in complete)/len(complete) if complete else None,
        "count":len(complete),"total":len(faculty),"contributors":[r["faculty"] for r in complete]}
    return result


def academic_reference(run_id,data):
    from services import ga_run_provenance
    try:
        record=ga_run_provenance.read(run_id)
        if record and record["technical_identity"]["input_fingerprint"]==data["metrics"]["input_fingerprint"]:
            return {"status":"UNVERIFIED","academic_year":record["academic_context"]["academic_year"],"term":record["academic_context"]["term"],
                "department":record["academic_context"]["department"],"dataset_id":record["academic_context"]["dataset_id"],"dataset_revision":record["academic_context"]["dataset_revision"]}
    except history.HistoryError:pass
    return None


def detail(run,generation,candidate):
    data=history.get_generation(run["run_id"],generation);selected=data[candidate]
    if data["engine_fingerprint"]!=run["engine_fingerprint"] or data["metrics"]["input_fingerprint"]!=run["input_fingerprint"]:reject("Snapshot and run input identity disagree.")
    report=reporting.generation_report(run["run_id"],generation,candidate)
    if report["source"]["chromosome_id"]!=selected["chromosome_id"]:reject("Analysis and candidate identities disagree.")
    context=context_for(data,selected)
    policy=context.get("preference_scoring_version") if context else None
    policy_key=sha(context) if context and policy in (1,2) and context.get("scorer_sha256") else None
    grouped=defaultdict(list)
    for row in selected["payload"]["schedule"]:
        if not str(row["faculty"]).startswith("external:"):grouped[reporting.normalized_code(row["faculty"])].append(row)
    if len(report["faculty"])>500:reject("Faculty analysis exceeds the bounded 500-row contract.")
    faculty=[]
    for member in report["faculty"]:
        code=member["faculty"].removeprefix("Faculty ");mine=grouped[code]
        indicators={row["key"]:row for row in member["preferences"] or []}
        percentages={key:indicators.get(key+"_preference",{}).get("satisfaction_percent") for key in KEYS}
        if any(v is not None and (not number(v) or not 0<=v<=100) for v in percentages.values()):reject("Invalid recorded satisfaction percentage.")
        captured=(context or {}).get("preferences",{}).get(code)
        preferred={k:captured.get(k) for k in ["preferred_subjects","preferred_days","preferred_start_time","preferred_end_time","preferred_schedule_blocks"] if k in captured} if isinstance(captured,dict) else None
        hours=meeting_hours(mine)
        faculty.append({"faculty":member["faculty"],"teaching_units":member["teaching_units"],"target":member["required_teaching_load"],
            "target_deviation":member["difference"],"preparations":len({r["subject"] for r in mine}),"satisfaction":percentages,
            "preference_status":{k:indicators.get(k+"_preference",{}).get("status","unavailable") for k in KEYS},
            "preference_explanations":{k:indicators.get(k+"_preference",{}).get("explanation","Not captured") for k in KEYS},
            "hours":hours,"weekly_hours":sum(hours.values()),"assignments":mine,"preferred":preferred,"unavailable_reason":member["unavailable_reason"]})
    faculty.sort(key=lambda x:(int(x["faculty"].removeprefix("Faculty ")) if x["faculty"].removeprefix("Faculty ").isdigit() else 10**12,x["faculty"]))
    mean=sum(r["teaching_units"] for r in faculty)/len(faculty) if faculty and all(number(r["teaching_units"]) for r in faculty) else None
    for row in faculty:row["average_deviation"]=row["teaching_units"]-mean if mean is not None else None
    validation=data["validation"]
    violations=sum(validation[k] for k in VIOLATIONS) if all(type(validation.get(k)) is int for k in VIOLATIONS) else None
    supported=context is not None and all(r["unavailable_reason"] is None for r in report["faculty"])
    return {"source":{"run_id":run["run_id"],"generation":generation,"candidate":candidate,"chromosome_id":selected["chromosome_id"],
        "input_fingerprint":data["metrics"]["input_fingerprint"],"engine_fingerprint":data["engine_fingerprint"],"configuration_fingerprint":data["metrics"]["configuration_fingerprint"]},
        "fitness":report["overall_penalty"],"faculty":faculty,"aggregates":aggregate(faculty),"captured_faculty_average":mean,
        "load_imbalance":sum(abs(r["average_deviation"]) for r in faculty)/len(faculty) if mean is not None else None,
        "conflicts":validation.get("conflicts"),"violations":violations,"elapsed_ms":data["metrics"].get("elapsed_ms"),
        "parameters":report["fitness_configuration"],"recorded_state":run["state"],"recorded_generation_count":len(run["generations"]),
        "reference_limits":{"preparations":(report["fitness_configuration"] or {}).get("max_preparations"),"hard_units":40 if supported else None},
        "policy_key":policy_key,"data":data,"context":context,"metric_basis":"CAPTURED_CONTEXT" if supported else "RECORDED_INDICATORS_OR_UNAVAILABLE"}


def project(run_id,generation=None,candidate="generation_best",history_offset=0):
    run=index(run_id)
    if not run["generations"]:reject("This run has no recorded chromosome snapshots.","GA_ADVANCED_EMPTY",404)
    generation=run["generations"][-1]["generation"] if generation is None else generation
    result=detail(run,generation,candidate);data=result.pop("data");context=result.pop("context");policy_key=result.pop("policy_key")
    try:
        from services import ga_evaluation_v2
        compatibility=ga_evaluation_v2.classify(run,data,ga_evaluation_v2.identity())
        compatibility={k:compatibility[k] for k in ["classification","reason"]}
    except history.HistoryError:compatibility={"classification":"UNKNOWN_COMPATIBILITY","reason":"CURRENT_CONTEXT_UNAVAILABLE"}
    end=max(0,len(run["generations"])-history_offset);window=run["generations"][max(0,end-50):end]
    points=[];choices=[];issues=[]
    for entry in window:
        point={"generation":entry["generation"],"best":None,"average":None,"subject":None,"day":None,"time":None,"violations":None,"elapsed_ms":None,
            "subject_count":None,"day_count":None,"time_count":None,"faculty_total":None}
        try:
            item=detail(run,entry["generation"],candidate)
            if (item["source"]["configuration_fingerprint"]!=result["source"]["configuration_fingerprint"] or item["data"]["metrics"].get("metrics_comparable") is not True
                or not policy_key or item["policy_key"]!=policy_key):
                reject("Incomparable historical observation.")
            point.update(best=item["data"]["metrics"]["best_ever_fitness"],average=item["data"]["metrics"]["average_fitness"],
                violations=item["violations"],elapsed_ms=item["elapsed_ms"],**{k:item["aggregates"][k]["value"] if item["metric_basis"]=="CAPTURED_CONTEXT" else None for k in KEYS})
            point.update(faculty_total=len(item["faculty"]),**{k+"_count":item["aggregates"][k]["count"] for k in KEYS})
            choices.extend({"generation":entry["generation"],"candidate":kind,"chromosome_id":item["data"][kind]["chromosome_id"]} for kind in KINDS)
        except (history.HistoryError,ValueError,KeyError,TypeError):issues.append({"generation":entry["generation"],"code":"OBSERVATION_UNAVAILABLE_OR_INCOMPATIBLE"})
        points.append(point)
    choices.extend({"generation":generation,"candidate":kind,"chromosome_id":data[kind]["chromosome_id"]} for kind in KINDS)
    unique={}
    for choice in choices:unique.setdefault(choice["chromosome_id"],choice)
    return {"schema_version":1,**result,"compatibility":compatibility,"receipt":receipt_status(run_id,data,run),
        "academic_context":academic_reference(run_id,data),
        "recorded_generations":sorted(set([generation,*[r["generation"] for r in window]])),
        "progress":points,"choices":list(unique.values()),"window":{"offset":history_offset,"total":len(run["generations"]),"older":end>50,"newer":history_offset>0},
        "issues":issues,"warnings":["Historical observations only; no CURRENT promotion or institutional approval.",
            "Faculty averages describe the captured cohort; roster completeness is unverified.",
            "Missing/disabled/non-applicable preferences are not zero satisfaction. Aggregate coverage is explicit.",
            "Recorded violations cover validated snapshots, not rejected search candidates.",
            "Chair access requires a verified run-to-department binding and is not enabled by this administrator interface."]}


def compare(run_id,left_generation,left_candidate,right_generation,right_candidate):
    run=index(run_id);left=detail(run,left_generation,left_candidate);right=detail(run,right_generation,right_candidate)
    if left["source"]["chromosome_id"]==right["source"]["chromosome_id"]:reject("Choose two distinct recorded chromosomes.","GA_ADVANCED_ONE_CANDIDATE",409)
    if any(item["data"]["metrics"].get("metrics_comparable") is not True for item in (left,right)) or any(left["source"][k]!=right["source"][k] for k in ["input_fingerprint","engine_fingerprint","configuration_fingerprint"]) or not left["policy_key"] or left["policy_key"]!=right["policy_key"]:
        reject("Snapshots do not establish matching captured policy, preferences, inputs and configuration.","GA_ADVANCED_INCOMPATIBLE",409)
    def delta(a,b):return b-a if number(a) and number(b) else None
    before={r["faculty"]:r for r in left["faculty"]};after={r["faculty"]:r for r in right["faculty"]}
    rows=[]
    for name in sorted(before.keys()|after.keys()):
        a=before.get(name);b=after.get(name)
        rows.append({"faculty":name,"before":a,"after":b,"changes":{k:delta(a.get(k) if a else None,b.get(k) if b else None) for k in ["teaching_units","preparations","average_deviation","target_deviation","weekly_hours"]},
            "satisfaction_changes":{k:delta(a["satisfaction"][k] if a else None,b["satisfaction"][k] if b else None) for k in KEYS}})
    same_cohort=set(before)==set(after)
    return {"schema_version":1,"run_id":run_id,"left":left["source"],"right":right["source"],"fitness":{"before":left["fitness"],"after":right["fitness"],"change":delta(left["fitness"],right["fitness"])},
        "load_imbalance":{"before":left["load_imbalance"],"after":right["load_imbalance"],"change":delta(left["load_imbalance"],right["load_imbalance"]) if same_cohort else None},
        "violations":{"before":left["violations"],"after":right["violations"],"change":delta(left["violations"],right["violations"])},
        "faculty":rows,"academic_compatibility":"UNKNOWN_COMPATIBILITY","receipt":receipt_status(run_id,right["data"],run),
        "explanation":"Right minus left. Lower fitness penalty is better; each satisfaction dimension must be inspected separately. This same-run recorded-context comparison does not establish institutional or CURRENT eligibility."}

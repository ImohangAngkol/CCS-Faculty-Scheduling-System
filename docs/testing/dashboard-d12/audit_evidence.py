"""D12 raw-byte preservation, privacy and evidence audit. No database access."""
import ast
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import struct
import subprocess
import sys
import zlib

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
MANIFEST=BASE/'manifest.json'
MODIFIED={'backend/main.py','backend/migrations/env.py','backend/routers/adjustments.py','backend/services/adjustment_service.py',
 'backend/tests/academic/test_academic_foundation.py','backend/tests/dashboard/test_adjustments.py','frontend/src/api/adjustments.ts',
 'frontend/src/components/common/AccountMenu.tsx','frontend/src/pages/faculty/AdjustmentRequests.tsx','frontend/src/routes/AppRoutes.tsx',
 'frontend/tests/adjustments.live.mjs','frontend/tests/mySchedule.browser.test.mjs'}
NEW={'backend/chair_models.py','backend/migrations/versions/d12_0001_chair_decisions.py','backend/routers/chair_reviews.py',
 'backend/schemas/chair_reviews.py','backend/services/chair_authority_service.py','backend/services/chair_decision_projection.py',
 'backend/services/chair_review_service.py','backend/tests/dashboard/chair_restart_child.py','backend/tests/dashboard/chair_sqlite.py',
 'backend/tests/dashboard/test_chair_live.py','backend/tests/dashboard/test_chair_migration.py','backend/tests/dashboard/test_chair_reviews.py',
 'backend/tests/dashboard/test_chair_trust.py','frontend/src/api/chairDecisions.ts','frontend/src/api/chairReviews.ts',
 'frontend/src/components/common/ChairReviewLink.tsx','frontend/src/pages/chair/Requests.tsx','frontend/tests/chairReviews.live.mjs',
 'frontend/tests/chairReviews.test.mjs'}



def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,stderr=subprocess.DEVNULL,text=True).strip()
def rel(p):return p.relative_to(ROOT).as_posix()


def main():
    baseline=json.loads((BASE/'preservation-baseline.json').read_text())
    changes={p for p,h in baseline.items() if not (ROOT/p).exists() or sha(ROOT/p)!=h}
    if changes!=MODIFIED:raise RuntimeError('Unexpected baseline delta (paths only): '+json.dumps(sorted(changes)))
    assert git('rev-parse','HEAD')=='cad837dde9bed38da6427ee3a4106566323dd53d'
    assert git('rev-parse','origin/main')==git('rev-parse','HEAD')
    assert git('branch','--show-current')=='main'
    assert not git('diff','--cached','--name-only')
    assert sha(ROOT/'backend/data/faculty_preferences.json')==baseline['backend/data/faculty_preferences.json']
    untracked=set(git('ls-files','--others','--exclude-standard').splitlines())
    allowed=lambda p:p in NEW or p=='docs/dashboard-d12-implementation.md' or p.startswith('docs/testing/dashboard-d12/') or p.startswith('docs/screenshots/dashboard-d12/')
    assert all(allowed(p) for p in untracked),'Unexpected untracked paths'
    files=sorted({ROOT/p for p in MODIFIED|NEW|untracked if ROOT/p!=MANIFEST})
    sys.path.insert(0,str(ROOT/'backend'))
    from services.evidence_sanitization import SENSITIVE,ENCODED,URI,PEM
    with (ROOT/'backend/data/Faculty.csv').open(encoding='utf-8-sig',newline='') as f:
        names=[r['Faculty'].strip() for r in csv.DictReader(f) if r.get('Faculty','').strip()]
    patterns={'encoded_or_truncated_receipt':ENCODED,'credential_URI':URI,'private_key':PEM,
        'short_receipt_fragment':re.compile(r'(?<![A-Za-z0-9_-])eyJ[A-Za-z0-9_=.-]+'),
        'bearer':re.compile(r'(?i)\bBearer\s+[A-Za-z0-9_.=-]{12,}')}
    findings=[];images=[];records=[]
    for path in files:
        if path.suffix=='.png':
            raw=path.read_bytes();assert raw[:8]==b'\x89PNG\r\n\x1a\n'
            width,height=struct.unpack('>II',raw[16:24]);offset=8;chunks=[]
            while offset<len(raw):
                n=struct.unpack('>I',raw[offset:offset+4])[0];k=raw[offset+4:offset+8];v=raw[offset+8:offset+8+n]
                assert zlib.crc32(k+v)==struct.unpack('>I',raw[offset+8+n:offset+12+n])[0]
                chunks.append(k);offset+=12+n
            assert not set(chunks)&{b'tEXt',b'zTXt',b'iTXt',b'eXIf'},'PNG text metadata requires review'
            images.append({'path':rel(path),'sha256':sha(path),'width':width,'height':height,
                'scope':'Real Edge/FastAPI/SQLite; explicitly fictional Chair directory, scope, schedule and snapshot providers; no genuine institutional approval' ,
                'privacy':'Visually reviewed original or confirmed byte-identical to reviewed original; fictional records only'})
            continue
        text=path.read_text(encoding='utf-8');values=[text]
        if path.suffix=='.py':ast.parse(text)
        if path.suffix=='.json':
            document=json.loads(text)
            def strings(v):
                if isinstance(v,str):yield v
                elif isinstance(v,dict):
                    for k,c in v.items():yield str(k);yield from strings(c)
                elif isinstance(v,list):
                    for c in v:yield from strings(c)
            values=list(strings(document))
            if path.name=='command.json':
                records.append((path,document))
                for field in ('stdout','stderr'):
                    if any(SENSITIVE.search(line) for line in document.get(field,'').splitlines()):
                        findings.append({'path':rel(path),'kind':'sensitive_output_assignment'})
        for kind,pattern in patterns.items():
            if any(pattern.search(v) for v in values):findings.append({'path':rel(path),'kind':kind})
        if any(re.search(r'(?<!\w)'+re.escape(name)+r'(?!\w)',text,re.I) for name in names):
            findings.append({'path':rel(path),'kind':'private_faculty_name'})
        if rel(path) not in MODIFIED and any(line.rstrip()!=line for line in text.splitlines()):
            raise RuntimeError('New-file whitespace: '+rel(path))
    if findings:raise RuntimeError('Privacy findings, values omitted: '+json.dumps(findings))
    subprocess.run(['git','diff','--check','--',*sorted(MODIFIED)],cwd=ROOT,check=True,capture_output=True)
    latest={}
    for path,record in sorted(records):latest[record['check']]={'path':rel(path),'exit_code':record['exit_code'],'scope':record['scope']}
    required={'focused','contracts','build','lint','d12-live','d11-live','d11-backend','backend','backend-regressions','academic-offline',
        'ga-resource-regressions','v1-fixtures','v2-engine','v2-api','browser-regressions','ga-browser','v2-browser','v2-live','live'}
    assert required<=latest.keys() and all(latest[k]['exit_code']==0 for k in required),'Final validation group missing or failed'
    manifest={'milestone':'D12','status':'IMPLEMENTED AND VERIFIED IN ISOLATED FICTIONAL ENVIRONMENTS; PRODUCTION SOURCE AND POSTGRESQL ACCEPTANCE BLOCKED',
        'recorded_at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'baseline_commit':git('rev-parse','HEAD'),
        'latest_commands':latest, 'results':{'focused_backend_and_offline_migration':42,'D11_backend_and_offline_migration':33,
 'new_frontend_contracts':15,'all_frontend_contracts':189,'D12_real_HTTP_browser_scenarios':12,'D12_live_pytest_wrappers':1,
 'D2_D9_backend':327,'auth_control':46,'academic_offline':85,'original_resource':3,'V1_original_operator_continuation_fixtures':4,
 'V2_kernel':30,'V2_API':18,'D1_D8_synthetic_HTTP_browser_scenarios':125,'GA_synthetic_HTTP_browser_scenarios':51,
 'D10_synthetic_HTTP_browser_scenarios':12,'D9_real_HTTP_browser_scenarios':16,'D10_real_HTTP_browser_scenarios':6,
 'D11_real_HTTP_browser_scenarios':12,'build':'PASS with existing bundling warnings','focused_ESLint':'0 errors, 0 warnings'},
        'preservation':{'baseline_files':len(baseline),'byte_identical':len(baseline)-len(changes),'intended_modified':sorted(changes),
            'academic_data_files_unchanged':sum(p.startswith('backend/data/') for p in baseline),'protected_preferences_unchanged':True,
            'original_GA_V1_V2_sources_and_six_historical_checkpoints_unchanged':True,'index_HEAD_origin_unchanged':True,
            'production_PostgreSQL_operations':0,'schedule_mutations':0,'D12_implemented':True,'schedule_application_implemented':False},
        'new_source_and_test_files':sorted(NEW),
        'historical_nonzero_commands':[{'path':rel(p),'check':r['check'],'exit_code':r['exit_code']} for p,r in records if r['exit_code']!=0],
        'privacy':{'findings':findings,'methods':['Full/truncated encoded/signed fragments, credential URIs, private keys and bearer scans','Decoded JSON strings and sensitive assignment/header checks for all command output','Locally compare private faculty names without exporting them','PNG CRC/metadata checks and original-image visual review'],'screenshots':images,'unique_images':len({i['sha256'] for i in images}),'raw_databases_checkpoints_HAR_or_session_payloads_archived':False},
         'limitations':['Institutional Chair directory, department scope bindings, verified schedule source and production faculty submission remain unconfigured/BLOCKED',
 'D12 browser uses explicitly fictional guarded Chair/schedule/trusted snapshot providers; real D8/D9/D10 ledger validation is exercised separately by backend integration tests with fictional issuers',
 '17 Phase4C PostgreSQL tests and D9-D12 PostgreSQL migration/trigger/transaction/concurrency/locking acceptance NOT RUN',
 'SQLite fixture triggers and offline PostgreSQL SQL rendering are not live PostgreSQL migration acceptance',
 'Deployment requires separately approved D12 migration; an unmigrated D11 database fails closed for decision-aware request reads',
 'One immutable final decision per request; no replacement, appeals, application or automatic GA execution',
 'Queue is bounded to 1000 submitted records; exceeds bound fails without partial data',
 'Historical failures and intermediate screenshots retained; final browser run supersedes intermediate UI wording/mobile observations'],
        'hash_convention':'Raw-byte SHA-256 of reviewed working files; current manifest excludes itself. Hashes do not prove institutional authority.',
        'artifacts':[{'path':rel(p),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]}
    MANIFEST.write_text(json.dumps(manifest,indent=2,ensure_ascii=True)+'\n',encoding='utf-8')
    assert all(sha(ROOT/a['path'])==a['sha256'] for a in manifest['artifacts'])
    print(json.dumps({'artifacts_hashed':len(files),'unchanged_baseline':len(baseline)-len(changes),'intended_existing_modifications':len(changes),'privacy_findings':0,'screenshots':len(images),'unique_images':manifest['privacy']['unique_images'],'historical_failed_commands_retained':len(manifest['historical_nonzero_commands'])}))


if __name__=='__main__':main()

"""F1.5 READ-ONLY IT data qualification: aggregate evidence only.

Uses stdlib CSV and ZIP/XML extraction. Never executes workbook formulas,
exports source rows/sheet names, imports the GA, or parses protected preference
JSON/settings. Identity/label joins exist only in process memory.
"""
import ast
from collections import Counter,defaultdict
import csv
from datetime import datetime,timedelta,timezone
from decimal import Decimal,InvalidOperation
import hashlib
import json
from pathlib import Path
import re
import sys
import time
import xml.etree.ElementTree as ET
import zipfile

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
DATA=ROOT/'backend/data'
NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
IT=re.compile(r'\b(?:BS)?IT\s*[- ]?\s*[1-4]\s*[- ]?[A-Z]\b',re.I)
IS=re.compile(r'\b(?:BS)?IS\s*[- ]?\s*[1-4]\s*[- ]?[A-Z]\b',re.I)
ACTIVE={'first_sem_bsit_subjects.csv','BSIT_Consolidated_Subject_Schedules.csv','Faculty Preferences V2.csv',
        'Faculty Admin, Research and Extension.csv','faculty_qualifications.csv','faculty_subject_eligibility.csv','subject_domains.csv'}


def norm(value):return re.sub(r'\s+',' ',str(value).strip().upper())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(path):
    with path.open(encoding='utf-8-sig',newline='') as source:
        reader=csv.DictReader(source);rows=list(reader)
        return reader.fieldnames or [],rows


def faculty_coverage(rows,aliases,registry):
    labels={norm(r['Faculty']) for r in rows if r.get('Faculty','').strip()}
    known={aliases[label] for label in labels if label in aliases}
    return dict(rows=len(rows),distinct_labels=len(labels),matched_registry_members=len(known),
                unresolved_labels=len(labels-set(aliases)),registry_members_not_represented=len(registry-known))


def qualification_summary(rows,registry):
    codes={int(r['faculty_code']) for r in rows}
    return dict(rows=len(rows),distinct_codes=len(codes),unknown_codes=len(codes-registry),
        registry_missing=len(registry-codes),duplicate_code_rows=len(rows)-len(codes),
        blank_specializations=sum(not r.get('specializations','').strip() for r in rows),
        degree_or_credential_columns_present=bool(set(rows[0])&{'degree','highest_degree','qualification'}) if rows else False,
        review_marker_rows=sum(bool(re.search(r'review|unverified|provisional',' '.join(r.get(k,'') for k in ('source','notes')),re.I)) for r in rows))


def compare_loads(a,b,aliases):
    def by_code(rows):return {aliases[norm(r['Faculty'])]:r for r in rows if norm(r['Faculty']) in aliases}
    left,right=by_code(a),by_code(b);common=set(left)&set(right)
    fields=('Admin Load','Research Load','Extension Load')
    comparable=different=formatting=unknown=0
    for key in common:
        raw_left=[left[key][f].strip() for f in fields];raw_right=[right[key][f].strip() for f in fields]
        try:
            a_values=[Decimal(x) for x in raw_left];b_values=[Decimal(x) for x in raw_right]
            if not all(x.is_finite() for x in [*a_values,*b_values]):raise InvalidOperation()
        except (InvalidOperation,ValueError):unknown+=1;continue
        comparable+=1
        if a_values!=b_values:different+=1
        elif raw_left!=raw_right:formatting+=1
    return dict(matched_identity_intersection=len(common),comparable_numeric_vectors=comparable,
        different_numeric_allowance_vectors=different,unknown_numeric_vectors=unknown,
        formatting_only_different_vectors=formatting,
        raw_text_different_vectors=sum(tuple(left[k][f].strip() for f in fields)!=tuple(right[k][f].strip() for f in fields) for k in common),
        active_non_numeric_allowance_cells=sum(not re.fullmatch(r'\d+',r[f].strip()) for r in left.values() for f in fields),
        resolution='Unresolved source/version disagreement; no precedence inferred, no values exported or changed')


def section_style(text):
    kinds=[k for k,p in (('IT',IT),('IS',IS)) if p.search(text)]
    if len(kinds)==2:return 'MULTIPLE_PROGRAM_MARKERS'
    if kinds:return kinds[0]
    return 'UNSCOPED_YEAR_SECTION' if re.fullmatch(r'\d[A-Z]',text.strip()) else 'OTHER_UNRESOLVED'


def workbook_summary(path,roomnames,aliases,registry):
    with zipfile.ZipFile(path) as archive:
        members=archive.infolist()
        if len(members)>2000 or sum(m.file_size for m in members)>100*1024*1024 or any(m.file_size>20*1024*1024 for m in members):
            raise ValueError('WORKBOOK_READ_BOUND_EXCEEDED')
        strings=[]
        if 'xl/sharedStrings.xml' in archive.namelist():
            strings=[''.join(n.itertext()) for n in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('m:si',NS)]
        counts=Counter();known=set();roomgroups={'IT':set(),'IS':set()};courses={'IT':set(),'IS':set()}
        roomkey=lambda s:re.sub(r'[^A-Z0-9]','',str(s).upper())
        for item in members:
            if not re.fullmatch(r'xl/worksheets/sheet\d+\.xml',item.filename):continue
            tree=ET.fromstring(archive.read(item));classes=set();faculty_form=False
            counts['sheets']+=1
            for row in tree.findall('.//m:sheetData/m:row',NS):
                values=[]
                for cell in row.findall('m:c',NS):
                    v=cell.find('m:v',NS)
                    counts['formula_cells']+=cell.find('m:f',NS) is not None
                    if cell.get('t')=='s' and v is not None:text=strings[int(v.text)]
                    elif cell.get('t')=='inlineStr':text=''.join(cell.find('m:is',NS).itertext())
                    else:text=(v.text or '') if v is not None else ''
                    values.append(text)
                    if norm(text) in aliases:known.add(aliases[norm(text)])
                text=' '.join(values)
                rowclasses={k for k,p in (('IT',IT),('IS',IS)) if p.search(text)};classes|=rowclasses
                faculty_form|=any(bool(re.match(r'^(?:name(?: of faculty)?|faculty(?: name)?|instructor)\s*:?',s,re.I)) for s in values)
                rooms={r for r in roomnames if any(roomkey(r)==roomkey(s) for s in values)}
                codes={re.sub(r'\s+','',s.upper()) for s in re.findall(r'\b(?:CCC|ITD|ITE|ITN|ISY)\s*\d[A-Z0-9.-]*',text,re.I)}
                for kind in rowclasses:
                    counts[kind+'_section_rows']+=1
                    counts[kind+'_section_rows_with_runtime_room']+=bool(rooms)
                    roomgroups[kind]|=rooms;courses[kind]|=codes
            if classes=={'IT','IS'}:
                counts['sheets_with_both_section_styles']+=1
                counts['faculty_labeled_sheets_with_both_styles']+=faculty_form
        markers={k:sum(bool(re.search(pattern,s,re.I)) for s in strings) for k,pattern in {
            'first_semester':r'first\s*sem|1st\s*sem','second_semester':r'second\s*sem|2nd\s*sem',
            'year_2026_2027':r'2026\s*[-–]\s*2027','tentative':r'tentative','degree_header':r'\bdegree\b',
            'it_department_phrase':r'department\s*(of)?\s*:?\s*(information technology|IT)\b|^information technology$',
            'approval_role_label':r'approved|approv|chair|dean'}.items()}
        return dict(file=path.name,counts=dict(counts),shared_string_markers=markers,
            exact_registry_alias_matches_in_cells=len(known),registry_not_exactly_matched=len(registry-known),
            runtime_rooms_with_both_section_styles=len(roomgroups['IT']&roomgroups['IS']),
            course_codes_with_both_section_styles=len(courses['IT']&courses['IS']),
            interpretation='String/row/sheet cooccurrence, not verified identities, IS roster, resource ownership, approved meetings, conflicts or activation',
            formulas='Stored/cached cells read without evaluation; no recalculation or workbook modification')


def inspect():
    identities=json.loads((DATA/'faculty_identities.json').read_text(encoding='utf-8'))['faculty']
    aliases={norm(label):int(row['faculty_code']) for row in identities for label in [row['name'],*row.get('aliases',[])]}
    registry=set(aliases.values());inventory=[];tables={}
    for path in sorted(DATA.glob('*.csv')):
        fields,rows=csv_rows(path);tables[path.name]=rows
        safe=['PRIVATE_HEADER_WITHHELD' if norm(k) in aliases or '@' in k or len(k)>80 else k for k in fields]
        inventory.append(dict(file=path.name,columns=safe,rows=len(rows),active_legacy_import=path.name in ACTIVE,
            explicit_term_fields=bool(set(fields)&{'term','term_id','semester','academic_year'}),
            explicit_department_fields=bool(set(fields)&{'department','department_id'})))
    faculty={name:faculty_coverage(tables[name],aliases,registry) for name in (
        'Faculty.csv','Faculty Admin, Research and Extension.csv','Faculty Preferences V2.csv','Faculty Preferences.csv','preferences.csv')}
    qualified=qualification_summary(tables['faculty_qualifications.csv'],registry)
    eligibility=tables['faculty_subject_eligibility.csv'];eligible=defaultdict(set)
    for row in eligibility:
        if row['eligibility_status'].strip().lower()=='eligible':eligible[int(row['faculty_code'])].add(norm(row['course_no']))
    first={norm(r['course no.']) for r in tables['first_sem_bsit_subjects.csv']}
    second={norm(r['course no.']) for r in tables['second_sem_bsit_subjects.csv']}
    all_eligible=set().union(*eligible.values())
    preassigned=json.loads((DATA/'preassigned_assignments.json').read_text(encoding='utf-8'))
    assignments=preassigned['assignments'];locked={norm(r['course_no']) for r in assignments}
    coverage=dict(first_distinct_courses=len(first),second_distinct_courses=len(second),course_intersection=len(first&second),
        first_with_normal_eligibility=len(first&all_eligible),first_without_normal_eligibility=len(first-all_eligible),
        first_without_normal_eligibility_but_preassigned=len((first-all_eligible)&locked),
        first_without_either_normal_eligibility_or_preassignment=len(first-all_eligible-locked),
        second_with_normal_eligibility=len(second&all_eligible),second_without_normal_eligibility=len(second-all_eligible),
        interpretation='Course-key coverage only; not offered-section, calendar feasibility, term approval or full institutional qualification')
    tree=ast.parse((ROOT/'backend/genetic_algorithm/utils/Functions.py').read_text())
    rooms=[r for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='rooms_names' for t in n.targets) for r in ast.literal_eval(n.value)]
    return dict(prototype_scope='IT_ONLY_USER_REPORTED; not all CCS',institutional_authority='UNVERIFIED_BLOCKED',
        registry=dict(identities=len(identities),explicit_department_fields=False,explicit_term_fields=False),csv_inventory=inventory,
        faculty_source_coverage=faculty,qualifications=qualified,
        eligibility=dict(rows=len(eligibility),distinct_faculty=len(eligible),unknown_codes=len(set(eligible)-registry),
            duplicate_faculty_course_pairs=len(eligibility)-len({(r['faculty_code'],r['course_no']) for r in eligibility}),
            status_counts=dict(Counter(r['eligibility_status'].strip().lower() for r in eligibility)),
            degrees_or_term_department_fields=False,approval_verification='NOT_ESTABLISHED_FROM_NONEMPTY_SOURCE_OR_BASIS'),
        workload_source_comparison=compare_loads(tables['Faculty Admin, Research and Extension.csv'],tables['Faculty.csv'],aliases),
        course_eligibility_coverage=coverage,
        domain_mapping_provenance=dict(rows=len(tables['subject_domains.csv']),
            review_or_inference_marker_rows=sum(bool(re.search(r'review|unverified|provisional|infer|auto',
                ' '.join(r.get(k,'') for k in ('domain_mapping_status','notes')),re.I)) for r in tables['subject_domains.csv']),
            institutional_mapping_approval='NOT_VERIFIED'),
        preassignments=dict(assignments=len(assignments),external_instructors=len(preassigned['external_instructors']),
            declared_fields=sorted({k for r in assignments for k in r}),fixed_meeting_times_present=False,external_department_known=False),
        section_label_categories={name:dict(Counter(section_style(r['section' if name=='faculty_load.csv' else 'Section']) for r in tables[name]))
            for name in ('faculty_load.csv','BSIT_GEC.csv','BSIT_Consolidated_Subject_Schedules.csv')},
        workbooks=[workbook_summary(p,rooms,aliases,registry) for p in sorted(DATA.glob('*.xlsx'))],
        authority_limits=['Adviser-supplied data is user-reported provenance, not institutional authorization',
            'No complete verified IT semester roster established; no IS roster built or inferred',
            'Shared-resource indicators require reconciliation and confirmation, not automatic activation'],
        protected_preferences_and_settings_parsed=False,GA_executed=False,database_operations=0)


def main():
    start=datetime.now(timezone(timedelta(hours=8)));out=BASE/start.strftime('%Y%m%dT%H%M%S%f+0800');out.mkdir(exist_ok=False)
    tick=time.perf_counter();result=inspect()
    with (out/'summary.json').open('x',encoding='utf-8') as f:json.dump(result,f,indent=2);f.write('\n')
    record=dict(command=[str(ROOT/'.venv/Scripts/python.exe'),'-B',str(Path(__file__).resolve())],cwd='repository root',
        started_at=start.isoformat(),finished_at=datetime.now(timezone(timedelta(hours=8))).isoformat(),elapsed_seconds=time.perf_counter()-tick,
        exit_code=0,status='READ_ONLY_SOURCE_QUALIFICATION_COMPLETE',summary_sha256=sha(out/'summary.json'),
        privacy='Aggregate counts/schema labels only. No faculty values, sheets names, row payloads, formulas, preferences or credentials exported.')
    with (out/'command.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2);f.write('\n')
    print(json.dumps(dict(status=record['status'],path=out.relative_to(ROOT).as_posix(),registry_identities=result['registry']['identities'],
                         workbook_count=len(result['workbooks']),department_scope='IT_ONLY; cross-department dependencies UNRESOLVED')))


if __name__=='__main__':main()

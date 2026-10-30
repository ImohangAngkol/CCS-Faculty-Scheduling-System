"""Fictional parser/aggregation controls; no institutional cohort constructed."""
import csv
from pathlib import Path
from types import SimpleNamespace
import zipfile

import pytest
import inspect_sources as review


@pytest.mark.parametrize('value,expected',[
    ('IT1A','IT'),('BSIT-2B','IT'),('IS1A','IS'),('BSIS 3B','IS'),
    ('1A','UNSCOPED_YEAR_SECTION'),('ISY101','OTHER_UNRESOLVED'),
    ('IT1A / IS2A','MULTIPLE_PROGRAM_MARKERS'),('Unknown','OTHER_UNRESOLVED')])
def test_section_labels_are_indicators_not_faculty_or_department_authority(value,expected):
    assert review.section_style(value)==expected


def test_exact_identity_joins_do_not_invent_members_or_fuzzy_aliases():
    rows=[{'Faculty':'Fictional A'},{'Faculty':'Fictional A'},{'Faculty':'Fictional unknown'}]
    result=review.faculty_coverage(rows,{'FICTIONAL A':900001},{900001,900002})
    assert result==dict(rows=3,distinct_labels=2,matched_registry_members=1,unresolved_labels=1,registry_members_not_represented=1)
    assert 'Fictional A' not in str(result) and 'Fictional unknown' not in str(result)


def test_specialization_coverage_is_not_degree_or_term_roster_verification():
    rows=[dict(faculty_code='900001',specializations='fictional-domain',source='fixture',notes='needs review')]
    result=review.qualification_summary(rows,{900001,900002})
    assert result['registry_missing']==1 and result['blank_specializations']==0
    assert result['degree_or_credential_columns_present'] is False and result['review_marker_rows']==1


@pytest.mark.parametrize('second,differences',[('4',0),('5',1),('4.0',0),('',0),('NaN',0)])
def test_allowance_disagreement_is_counted_without_picking_authority(second,differences):
    first=[{'Faculty':'Fictional A','Admin Load':'4','Research Load':'0','Extension Load':'0'}]
    other=[dict(first[0],**{'Admin Load':second})]
    result=review.compare_loads(first,other,{'FICTIONAL A':900001})
    assert result['different_numeric_allowance_vectors']==differences and result['matched_identity_intersection']==1
    assert result['unknown_numeric_vectors']==int(second in ('','NaN'))
    if second=='4.0':assert result['formatting_only_different_vectors']==1
    assert 'Fictional A' not in str(result)


def test_csv_inspection_preserves_source_bytes(tmp_path):
    path=tmp_path/'fictional.csv';path.write_text('Faculty,Admin Load\nFictional A,4\n',encoding='utf-8')
    before=path.read_bytes();headers,rows=review.csv_rows(path)
    assert headers==['Faculty','Admin Load'] and len(rows)==1 and path.read_bytes()==before


def test_workbook_cooccurrence_is_not_a_unique_person_roster_or_constraint(tmp_path):
    path=tmp_path/'fictional.xlsx'
    namespace='http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    xml=f'''<worksheet xmlns="{namespace}"><sheetData>
      <row r="1"><c r="A1" t="inlineStr"><is><t>Faculty name:</t></is></c></row>
      <row r="2"><c r="A2" t="inlineStr"><is><t>IT1A</t></is></c><c r="B2" t="inlineStr"><is><t>Fictional room</t></is></c></row>
      <row r="3"><c r="A3" t="inlineStr"><is><t>IS1A</t></is></c><c r="B3" t="inlineStr"><is><t>Fictional room</t></is></c><c r="C3"><f>1+1</f><v>2</v></c></row>
    </sheetData></worksheet>'''
    with zipfile.ZipFile(path,'w') as archive:archive.writestr('xl/worksheets/sheet1.xml',xml)
    before=path.read_bytes();result=review.workbook_summary(path,['Fictional room'],{},set())
    assert result['counts']['faculty_labeled_sheets_with_both_styles']==1
    assert result['runtime_rooms_with_both_section_styles']==1 and result['counts']['formula_cells']==1
    assert 'Fictional room' not in str(result) and path.read_bytes()==before
    assert 'not verified identities' in result['interpretation']


def test_oversized_workbook_is_rejected_before_parsing(monkeypatch):
    class FakeArchive:
        def __enter__(self):return self
        def __exit__(self,*args):return False
        def infolist(self):return [SimpleNamespace(file_size=21*1024*1024)]
    monkeypatch.setattr(review.zipfile,'ZipFile',lambda path:FakeArchive())
    with pytest.raises(ValueError,match='WORKBOOK_READ_BOUND_EXCEEDED'):
        review.workbook_summary(Path('fictional.xlsx'),[],{},set())

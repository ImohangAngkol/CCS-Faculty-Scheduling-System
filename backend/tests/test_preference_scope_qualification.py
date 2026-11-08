"""Actual auth and preference HTTP handlers with fictional metadata/SQLite."""
from types import SimpleNamespace
import pytest
from tests.test_deployment_identity_qualification import identity,FACULTY,OTHER

@pytest.fixture
def preferences(identity,monkeypatch,tmp_path):
    from routers import preferences as router
    from services import preference_authorization as auth,preference_validation_service as validation
    path=tmp_path/'fictional-preferences.json';path.write_text('[]',encoding='utf-8')
    def resolve(code):
        if code not in (0,1):raise ValueError('Unknown fictional resource')
        return SimpleNamespace(stable_id=FACULTY if code==0 else OTHER)
    for module in [router,auth,validation]:monkeypatch.setattr(module,'resolve_normal_faculty',resolve)
    monkeypatch.setattr(validation,'list_subject_metadata',lambda *_a,**_k:[])
    monkeypatch.setattr(router,'PREFERENCE_FILE',path)
    return identity,path

def test_own_preference_survives_reads_other_faculty_is_unchanged(preferences):
    f,path=preferences;headers=f.login();out=f.client.put('/preferences/0',headers=headers,json={'preferred_days':['M']})
    assert out.status_code==200 and out.json()['preferred_days']==['M']
    assert f.client.get('/preferences/0').json()['preferred_days']==['M']
    before=path.read_bytes()
    denied=f.client.put('/preferences/1',headers=headers,json={'preferred_days':['T']});assert denied.status_code==403
    assert path.read_bytes()==before

@pytest.mark.parametrize('claim',['headers','query'])
def test_forged_admin_or_department_never_grants_cross_faculty_write(preferences,claim):
    f,path=preferences;headers=f.login();headers.update({'X-Role':'admin','X-Department-ID':'FICTIONAL-OTHER','X-Faculty-ID':OTHER})
    before=path.read_bytes();url='/preferences/1'+('?role=admin&department=FICTIONAL-OTHER' if claim=='query' else '')
    denied=f.client.put(url,headers=headers,json={'preferred_days':['T']});assert denied.status_code==403
    assert path.read_bytes()==before

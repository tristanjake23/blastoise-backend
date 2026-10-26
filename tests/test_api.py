from contextlib import contextmanager
from datetime import date,timedelta
from decimal import Decimal
from uuid import UUID
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app.main import create_app
from app.auth import User,current_user,require,ADMIN,CLINICAL,BILLING
from app import db
from app.models import Login,Patient,Invoice,Payment,Prescription,Schedule
from app.routes import billing

UID=UUID('10000000-0000-0000-0000-000000000001')
CLINIC=UUID('20000000-0000-0000-0000-000000000001')
USER=User(UID,CLINIC,'clinic_admin','Test admin','not-a-real-token')

@pytest.fixture
def client():
    app=create_app()
    with TestClient(app) as c:yield c

def test_health_without_secret_configuration(client):
    assert client.get('/health').status_code==200

@pytest.mark.parametrize('path',['/api/patients','/api/doctors','/api/schedules','/api/appointments','/api/consultations','/api/prescriptions','/api/invoices','/api/dashboard','/api/triage'])
def test_private_routes_reject_anonymous(client,path):
    assert client.get(path).status_code==401

def test_validation_does_not_echo_password(client):
    response=client.post('/api/auth/login',json={'email':'x','password':'SECRET_TEST_VALUE','unexpected':1})
    assert response.status_code==422
    assert 'SECRET_TEST_VALUE' not in response.text

def test_password_whitespace_preserved():
    assert Login(email='a@b.com',password='  valid password  ').password=='  valid password  '

@pytest.mark.parametrize('role,roles,allowed',[('doctor',BILLING,False),('staff',CLINICAL,False),('doctor',CLINICAL,True),('clinic_admin',ADMIN,True)])
def test_role_matrix(role,roles,allowed):
    user=User(UID,CLINIC,role,'Test','token')
    if allowed:require(user,roles)
    else:
        with pytest.raises(HTTPException) as e:require(user,roles)
        assert e.value.status_code==403

def test_future_dob_and_tenant_injection_rejected():
    with pytest.raises(ValueError):Patient(full_name='Test',date_of_birth=date.today()+timedelta(days=1))
    with pytest.raises(ValueError):Patient(full_name='Test',clinic_id=CLINIC)

def test_negative_money_and_empty_prescription_rejected():
    with pytest.raises(ValueError):Payment(amount=-1,method='cash',reference='test')
    with pytest.raises(ValueError):Prescription(consultation_id=UID,items=[])
    with pytest.raises(ValueError):Payment(amount='NaN',method='cash',reference='test')

class Cursor:
    def __init__(self,row):self.row=row
    def fetchone(self):return self.row
class FakeConn:
    def __init__(self):self.calls=[];self.rolled_back=False
    def execute(self,query,params=()):self.calls.append((query,params));return Cursor({'id':UID})
    @contextmanager
    def transaction(self):
        try:yield
        except Exception:self.rolled_back=True;raise
class FakePool:
    def __init__(self,conn):self.conn=conn
    @contextmanager
    def connection(self,timeout):yield self.conn

def test_user_database_scope_uses_transaction_local_role():
    from types import SimpleNamespace
    conn=FakeConn();request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(pool=FakePool(conn))))
    with db.connection(request,USER):pass
    assert any(q=='SET LOCAL ROLE authenticated' for q,p in conn.calls)
    assert any(str(UID) in p for q,p in conn.calls)
    assert all('SET ROLE postgres' not in str(q) for q,p in conn.calls)

def test_transaction_rolls_back_on_failure():
    from types import SimpleNamespace
    conn=FakeConn();request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(pool=FakePool(conn))))
    with pytest.raises(RuntimeError):
        with db.connection(request,USER):raise RuntimeError('fail')
    assert conn.rolled_back

def test_sql_injection_payload_is_bound_parameter():
    conn=FakeConn();attack="Robert'); DROP TABLE public.patients; --"
    db.insert(conn,'patients',{'full_name':attack,'clinic_id':CLINIC})
    query,params=conn.calls[-1]
    assert attack not in query.as_string()
    assert attack in params

def test_doctor_cannot_create_invoice_before_database_access(client):
    client.app.dependency_overrides[current_user]=lambda:User(UID,CLINIC,'doctor','Doctor','token')
    response=client.post('/api/invoices',json={'patient_id':str(UID),'due_date':str(date.today()),'items':[{'description':'Fee','quantity':1,'unit_price':100}]})
    assert response.status_code==403

def test_staff_cannot_read_clinical_records(client):
    client.app.dependency_overrides[current_user]=lambda:User(UID,CLINIC,'staff','Staff','token')
    assert client.get('/api/prescriptions').status_code==403
    assert client.get('/api/consultations').status_code==403

def test_cors_allows_expected_local_origin(client):
    response=client.options('/api/patients',headers={'Origin':'http://localhost:5173','Access-Control-Request-Method':'GET','Access-Control-Request-Headers':'authorization'})
    assert response.status_code==200
    assert response.headers['access-control-allow-origin']=='http://localhost:5173'
    assert 'access-control-allow-origin' not in client.get('/health',headers={'Origin':'https://untrusted.example'}).headers

def test_openapi_primary_entities_have_crud(client):
    schema=client.get('/openapi.json').json()['paths']
    for path in ['patients','doctors','schedules','prescriptions','invoices']:
        assert {'get','post'}<=set(schema['/api/'+path])
        assert {'put','delete'}<=set(schema['/api/'+path+'/{row_id}'])

def test_all_responses_no_store(client):
    assert client.get('/health').headers['cache-control']=='no-store'

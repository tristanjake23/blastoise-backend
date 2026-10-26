from types import SimpleNamespace
import httpx
import pytest
from fastapi import HTTPException
from app.auth import auth_call
from app.models import Doctor

@pytest.mark.parametrize('path', ['/doctors/a.jpg','https://example.com/a.jpg'])
def test_doctor_photo_paths(path):
    assert Doctor(full_name='Clinic doctor',specialty='Family Medicine',photo_url=path).photo_url==path

@pytest.mark.parametrize('path',['javascript:alert(1)','http://example.com/a.jpg','/doctors/../private.txt'])
def test_unsafe_photo_paths(path):
    with pytest.raises(ValueError):Doctor(full_name='Doctor',specialty='Family Medicine',photo_url=path)

def test_new_doctor_private_by_default():
    doctor=Doctor(full_name='Doctor',specialty='Family Medicine')
    assert not doctor.is_published and not doctor.is_archived and not doctor.is_sample

@pytest.mark.parametrize('code,status,expected', [('invalid_credentials',400,'login password'),('email_not_confirmed',400,'Confirm your account'),('bad_jwt',401,'Session expired')])
def test_auth_errors_are_actionable_and_do_not_echo_secrets(monkeypatch,code,status,expected):
    import app.auth as auth
    monkeypatch.setattr(auth,'settings',SimpleNamespace(supabase_publishable_key='test-key',supabase_url='https://example.com'))
    client=httpx.Client(transport=httpx.MockTransport(lambda request:httpx.Response(status,json={'code':code,'message':'DO_NOT_ECHO_SECRET'})))
    request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(http=client)))
    with pytest.raises(HTTPException) as error:auth_call(request,'POST','token?grant_type=password',payload={'password':'PRIVATE'})
    assert expected in error.value.detail
    assert 'PRIVATE' not in error.value.detail and 'DO_NOT_ECHO' not in error.value.detail

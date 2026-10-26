from dataclasses import dataclass
from uuid import UUID
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from .config import settings
from .db import connection,one
bearer=HTTPBearer(auto_error=False)
ROLES={"clinic_admin","doctor","staff","clinic_member"}
ADMIN={"clinic_admin"}
CLINICAL={"clinic_admin","doctor"}
BILLING={"clinic_admin","staff","clinic_member"}
ALL=ROLES

@dataclass(frozen=True)
class User:
    id: UUID
    clinic_id: UUID
    role: str
    full_name: str
    token: str


def auth_call(request, method, path, token=None, payload=None):
    if not settings.supabase_publishable_key or settings.supabase_publishable_key.startswith(("PALITAN", "IPASTE", "replace_")):
        raise HTTPException(503,"Set SUPABASE_PUBLISHABLE_KEY in backend/.env.")
    headers={"apikey":settings.supabase_publishable_key}
    if token: headers['Authorization']='Bearer '+token
    response=request.app.state.http.request(method,settings.supabase_url+'/auth/v1/'+path,headers=headers,json=payload)
    if response.status_code>=500: raise HTTPException(503,"Authentication provider unavailable.")
    if response.status_code>=400:
        try: code=response.json().get('code','')
        except ValueError: code=''
        if code in ('bad_jwt','invalid_jwt','refresh_token_not_found','refresh_token_already_used'):
            raise HTTPException(401,"Session expired. Please sign in again.")
        if code=='email_not_confirmed':raise HTTPException(401,"Confirm your account email before signing in.")
        if response.status_code==429:raise HTTPException(429,"Too many sign-in requests. Please wait and try again.")
        if code=='invalid_credentials':raise HTTPException(401,"Email or login password is incorrect. Use your Auth account password, not the database password.")
        if response.status_code in (401,403) and not token and code!='invalid_credentials':
            raise HTTPException(401,"Sign-in failed. Check the Auth account credentials and backend publishable key.")
        raise HTTPException(401,"Sign-in failed or session expired.")
    return response.json() if response.content else {}


def identity(request, token):
    verified=auth_call(request,'GET','user',token=token)
    try: uid=UUID(verified['id'])
    except (KeyError,ValueError): raise HTTPException(401,"Invalid authenticated identity.")
    with connection(request,readonly=True) as conn:
        profile=conn.execute('SELECT id,clinic_id,role,full_name FROM public.profiles WHERE id=%s',(uid,)).fetchone()
    if not profile or not profile['clinic_id'] or profile['role'] not in ROLES:
        raise HTTPException(403,"Your account needs an assigned clinic and approved role. Contact the administrator.")
    return User(uid,profile['clinic_id'],profile['role'],profile['full_name'] or 'Clinic member',token)


def current_user(request:Request, credentials:HTTPAuthorizationCredentials|None=Depends(bearer)):
    if not credentials or credentials.scheme.lower()!='bearer': raise HTTPException(401,"Sign in to access the clinic.",headers={"WWW-Authenticate":"Bearer"})
    return identity(request,credentials.credentials)


def require(user,roles):
    if user.role not in roles: raise HTTPException(403,"Your role is not allowed to perform this operation.")


def profile_json(user):
    return {"id":str(user.id),"clinic_id":str(user.clinic_id),"role":user.role,"full_name":user.full_name}

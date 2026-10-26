from collections import defaultdict,deque
from threading import Lock
from time import monotonic
from fastapi import APIRouter,Depends,HTTPException,Request
from ..auth import auth_call,identity,current_user,profile_json
from ..models import Login,Refresh
router=APIRouter(prefix='/auth',tags=['Authentication'])
_attempts=defaultdict(deque)
_lock=Lock()
def throttle(request):
    key=request.client.host if request.client else 'unknown'
    now=monotonic()
    with _lock:
        for old in list(_attempts):
            if not _attempts[old] or _attempts[old][-1]<now-60: del _attempts[old]
        bucket=_attempts[key]
        while bucket and bucket[0]<now-60:bucket.popleft()
        if len(bucket)>=10:raise HTTPException(429,'Too many sign-in attempts. Wait one minute.')
        bucket.append(now)

def session(request,data):
    user=identity(request,data['access_token'])
    return {k:data[k] for k in ['access_token','refresh_token','expires_in','token_type'] if k in data}|{'profile':profile_json(user)}
@router.post('/login')
def login(body:Login,request:Request):
    throttle(request)
    return session(request,auth_call(request,'POST','token?grant_type=password',payload=body.model_dump()))
@router.post('/refresh')
def refresh(body:Refresh,request:Request):
    throttle(request)
    return session(request,auth_call(request,'POST','token?grant_type=refresh_token',payload=body.model_dump()))
@router.get('/me')
def me(user=Depends(current_user)):return profile_json(user)
@router.post('/logout')
def logout(request:Request,user=Depends(current_user)):
    auth_call(request,'POST','logout?scope=local',token=user.token)
    return {'ok':True}

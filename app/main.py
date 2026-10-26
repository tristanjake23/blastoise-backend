from contextlib import asynccontextmanager
import httpx
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool,PoolTimeout
from fastapi import FastAPI,Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .routes import auth_routes,records,public,clinical,billing

@asynccontextmanager
async def lifespan(app):
    app.state.http=httpx.Client(timeout=15,follow_redirects=False)
    app.state.pool=ConnectionPool(settings.database_url,min_size=0,max_size=5,timeout=10,open=True,kwargs={'row_factory':dict_row,'autocommit':True,'prepare_threshold':None,'connect_timeout':10}) if settings.database_url else None
    yield
    app.state.http.close()
    if app.state.pool:app.state.pool.close()

def create_app():
    app=FastAPI(title='Blastoise Healthcare API',version='1.0.0',lifespan=lifespan)
    app.add_middleware(CORSMiddleware,allow_origins=list(settings.cors_origins),allow_credentials=False,allow_methods=['GET','POST','PUT','PATCH','DELETE','OPTIONS'],allow_headers=['Authorization','Content-Type'])
    @app.middleware('http')
    async def headers(request,call_next):
        response=await call_next(request)
        response.headers['Cache-Control']='no-store'
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='no-referrer'
        return response
    @app.exception_handler(RequestValidationError)
    async def validation_error(request,exc):
        # Do not echo submitted passwords, tokens or medical payloads in errors.
        return JSONResponse(status_code=422,content={'detail':[{'loc':list(e['loc']),'msg':e['msg'],'type':e['type']} for e in exc.errors()]})
    @app.exception_handler(psycopg.Error)
    async def database_error(request,exc):
        if exc.sqlstate in ('23505','23P01'):code,message=409,'Duplicate record or overlapping appointment slot.'
        elif exc.sqlstate=='23503':code,message=409,'Related record is missing, belongs to another clinic, or is still in use.'
        elif exc.sqlstate in ('23514','22003','22001'):code,message=422,'Record violates a database validation rule.'
        elif exc.sqlstate=='42501':code,message=403,'Database permissions do not allow this operation.'
        elif exc.sqlstate=='P0001':code,message=409,'Operation conflicts with a clinic rule. Check appointment availability, invoice balance, or record status.'
        else:code,message=503,'Database operation failed. Check the backend connection and schema.'
        return JSONResponse(status_code=code,content={'detail':message})
    @app.exception_handler(PoolTimeout)
    async def pool_error(request,exc):return JSONResponse(status_code=503,content={'detail':'Database connection unavailable. Check DATABASE_URL and pooler settings.'})
    @app.exception_handler(httpx.HTTPError)
    async def auth_network_error(request,exc):return JSONResponse(status_code=503,content={'detail':'Authentication service is temporarily unavailable.'})
    @app.get('/health')
    def health():return {'status':'ok','database_configured':bool(settings.database_url),'auth_configured':bool(settings.supabase_publishable_key)}
    for router in (auth_routes.router,public.router,records.router,clinical.router,billing.router):app.include_router(router,prefix='/api')
    return app
app=create_app()

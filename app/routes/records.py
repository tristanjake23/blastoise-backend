from uuid import UUID
from fastapi import APIRouter,Depends,Query,Request
from psycopg import sql
from ..auth import current_user,require,ADMIN,ALL
from ..db import connection,one,insert,update,delete
from ..models import Patient,Doctor,Schedule
router=APIRouter(tags=['Clinic records'])

def register(path,table,model,write_roles=ALL):
    def list_records(request:Request,user=Depends(current_user),limit:int=Query(100,ge=1,le=200),offset:int=Query(0,ge=0)):
        with connection(request,user,readonly=True) as conn:
            return conn.execute(sql.SQL('SELECT * FROM public.{} WHERE clinic_id=%s ORDER BY id LIMIT %s OFFSET %s').format(sql.Identifier(table)),(user.clinic_id,limit,offset)).fetchall()
    def read_record(row_id:UUID,request:Request,user=Depends(current_user)):
        with connection(request,user,readonly=True) as conn:
            return one(conn,sql.SQL('SELECT * FROM public.{} WHERE id=%s AND clinic_id=%s').format(sql.Identifier(table)),(row_id,user.clinic_id))
    def create_record(body,request:Request,user=Depends(current_user)):
        require(user,write_roles)
        with connection(request,user) as conn:return insert(conn,table,body.model_dump()|{'clinic_id':user.clinic_id})
    create_record.__annotations__['body']=model
    def replace_record(row_id:UUID,body,request:Request,user=Depends(current_user)):
        require(user,write_roles)
        with connection(request,user) as conn:return update(conn,table,row_id,user.clinic_id,body.model_dump())
    replace_record.__annotations__['body']=model
    def delete_record(row_id:UUID,request:Request,user=Depends(current_user)):
        require(user,ADMIN)
        with connection(request,user) as conn:return delete(conn,table,row_id,user.clinic_id)
    for function in (list_records,read_record,create_record,replace_record,delete_record):function.__name__=table+'_'+function.__name__
    router.add_api_route(path,list_records,methods=['GET'])
    router.add_api_route(path+'/{row_id}',read_record,methods=['GET'])
    router.add_api_route(path,create_record,methods=['POST'],status_code=201)
    router.add_api_route(path+'/{row_id}',replace_record,methods=['PUT'])
    router.add_api_route(path+'/{row_id}',delete_record,methods=['DELETE'])
register('/patients','patients',Patient)
register('/doctors','doctors',Doctor,ADMIN)
register('/schedules','doctor_schedules',Schedule)

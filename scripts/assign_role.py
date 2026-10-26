"""Assign a clinic and role to an EXISTING Supabase Auth user. Trusted local admin CLI only."""
import argparse,sys
from uuid import UUID
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from app.config import settings
parser=argparse.ArgumentParser()
parser.add_argument('--email',required=True)
parser.add_argument('--clinic-id',required=True,type=UUID)
parser.add_argument('--role',required=True,choices=['clinic_admin','doctor','staff'])
args=parser.parse_args()
if not settings.database_url:raise SystemExit('Set DATABASE_URL first.')
with psycopg.connect(settings.database_url) as conn:
    user=conn.execute('SELECT id FROM auth.users WHERE lower(email)=lower(%s)',(args.email,)).fetchone()
    if not user:raise SystemExit('Create the user in Supabase Authentication > Users first.')
    if not conn.execute('SELECT id FROM public.clinics WHERE id=%s',(args.clinic_id,)).fetchone():raise SystemExit('Clinic not found.')
    updated=conn.execute('UPDATE public.profiles SET clinic_id=%s,role=%s WHERE id=%s RETURNING id',(args.clinic_id,args.role,user[0])).fetchone()
    if not updated:raise SystemExit('No profile exists for this Auth user. Verify the auth-user profile trigger before assigning access.')
    print('Existing user assigned to clinic and role. No password was changed.')

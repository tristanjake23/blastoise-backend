"""Read-only setup check. Does not print credentials."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from app.config import settings
url=settings.database_url
if not url:raise SystemExit('Missing DATABASE_URL in blastoise-backend/.env. Copy .env.example first.')
if not url.startswith(('postgresql://','postgres://')):raise SystemExit('DATABASE_URL must start with postgresql://. Do not repeat DATABASE_URL= inside its value.')
try:
    with psycopg.connect(url,connect_timeout=10) as conn:
        conn.execute('SET TRANSACTION READ ONLY')
        tables={r[0] for r in conn.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")}
        required={'patients','doctors','doctor_schedules','appointments','consultations','prescriptions','prescription_items','invoices','invoice_items','payments','profiles'}
        if required-tables:raise SystemExit('Missing tables: '+', '.join(sorted(required-tables)))
        columns={r[0] for r in conn.execute("SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name='doctors'")}
        if not {'is_published','is_archived'}<=columns:raise SystemExit('Database connected. Run doctor-publication.sql in Supabase SQL Editor for this revision.')
        print('Connection OK. Healthcare tables found:',len(tables))
        print('Auth key configured:',bool(settings.supabase_publishable_key and not settings.supabase_publishable_key.startswith('replace_')))
except psycopg.Error as e:
    msg=str(e).lower()
    if 'password authentication failed' in msg:reason='Database password rejected. Use the saved database password, not your Auth login password.'
    elif 'tenant or user not found' in msg:reason='Check project ref, pooler host and postgres.PROJECT_REF username.'
    elif 'timeout' in msg:reason='Connection timed out. Check network and project availability.'
    elif 'ssl' in msg or 'certificate' in msg:reason='TLS connection failed. Check sslmode=require and system certificates.'
    else:
        from urllib.parse import urlsplit, unquote

        reason = str(e).replace(url, "[DATABASE_URL]")
        password = urlsplit(url).password
        if password:
            reason = reason.replace(password, "[HIDDEN]")
            reason = reason.replace(unquote(password), "[HIDDEN]")
    raise SystemExit(reason)

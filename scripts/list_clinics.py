import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import psycopg
from app.config import settings
with psycopg.connect(settings.database_url) as conn:
    conn.execute('SET TRANSACTION READ ONLY')
    for row in conn.execute('SELECT id,name FROM public.clinics ORDER BY name'):
        print(str(row[0]),row[1])

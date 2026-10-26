
SELECT tablename, rowsecurity
FROM pg_tables WHERE schemaname='public' ORDER BY tablename;
SELECT schemaname, tablename, policyname, roles, cmd, qual, with_check
FROM pg_policies WHERE schemaname='public' ORDER BY tablename,policyname;
SELECT c.relname, c.reloptions
FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='public' AND c.relkind='v';

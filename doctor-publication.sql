-- Run ONCE in the EXISTING project's SQL Editor, before using this revision.
-- Additive change only: no patient rows, invoices or doctor rows are deleted.
BEGIN;
ALTER TABLE public.doctors ADD COLUMN IF NOT EXISTS is_published boolean NOT NULL DEFAULT false;
ALTER TABLE public.doctors ADD COLUMN IF NOT EXISTS is_archived boolean NOT NULL DEFAULT false;
ALTER TABLE public.doctors ALTER COLUMN is_sample SET DEFAULT false;
-- Existing profiles remain private until an admin verifies and publishes them.
COMMIT;

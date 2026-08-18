-- This script dynamically drops EVERY table in the public schema. 
-- WARNING: This will completely wipe all data and tables.

DO $$ DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname = 'public') LOOP
        EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
END $$;

-- Drop the RPC function just in case
DROP FUNCTION IF EXISTS get_drug_monthly_totals(TEXT);

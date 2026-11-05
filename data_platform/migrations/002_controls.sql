-- Run as migration owner, PostgreSQL 15+. Application agents never receive this role.
DO $$ BEGIN
 IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname='finagent_reader') THEN
 CREATE ROLE finagent_reader NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE;
 END IF;
END $$;
ALTER ROLE finagent_reader SET statement_timeout='5s';
ALTER ROLE finagent_reader SET default_transaction_read_only=on;
GRANT USAGE ON SCHEMA ads TO finagent_reader;
GRANT SELECT ON ads.finance_dashboard TO finagent_reader;
-- Owner views bypass table RLS: explicitly scope the exposed view itself.
CREATE OR REPLACE VIEW ads.finance_dashboard WITH (security_barrier=true) AS
SELECT *,revenue-cost gross_profit,revenue-cost-expense operating_profit,
(revenue-cost)/nullif(revenue,0) gross_margin
FROM dws.monthly_finance
WHERE organization_id = nullif(current_setting('app.organization_id',true),'');
CREATE OR REPLACE FUNCTION dwd.assert_voucher_balance() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE r record;
BEGIN
 FOR r IN SELECT DISTINCT organization_id,source_system,voucher_no,posting_date,currency
 FROM (SELECT NEW.organization_id organization_id,NEW.source_system source_system,NEW.voucher_no voucher_no,NEW.posting_date posting_date,NEW.currency currency
 UNION SELECT OLD.organization_id,OLD.source_system,OLD.voucher_no,OLD.posting_date,OLD.currency) k
 WHERE organization_id IS NOT NULL LOOP
 IF EXISTS(SELECT 1 FROM dwd.fact_journal_entry f WHERE
 (f.organization_id,f.source_system,f.voucher_no,f.posting_date,f.currency)=
 (r.organization_id,r.source_system,r.voucher_no,r.posting_date,r.currency)
 GROUP BY f.organization_id HAVING sum(debit)<>sum(credit)) THEN
 RAISE EXCEPTION 'Unbalanced voucher' USING ERRCODE='23514';
 END IF;
 END LOOP;
 RETURN NULL;
END $$;
DROP TRIGGER IF EXISTS voucher_balance ON dwd.fact_journal_entry;
CREATE CONSTRAINT TRIGGER voucher_balance AFTER INSERT OR UPDATE OR DELETE ON dwd.fact_journal_entry
DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION dwd.assert_voucher_balance();

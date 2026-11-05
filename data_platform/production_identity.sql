-- Optional production overlay. Run only as a dedicated migration owner.
CREATE SCHEMA IF NOT EXISTS identity;
REVOKE ALL ON SCHEMA identity FROM PUBLIC;
CREATE TABLE IF NOT EXISTS identity.login_organization(login_name name PRIMARY KEY, organization_id text NOT NULL);
REVOKE ALL ON identity.login_organization FROM PUBLIC;
CREATE OR REPLACE FUNCTION identity.organization() RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path=pg_catalog AS
$$ SELECT organization_id FROM identity.login_organization WHERE login_name=session_user $$;
REVOKE ALL ON FUNCTION identity.organization() FROM PUBLIC;
GRANT USAGE ON SCHEMA identity TO finagent_reader;
GRANT EXECUTE ON FUNCTION identity.organization() TO finagent_reader;
CREATE OR REPLACE VIEW ads.finance_dashboard WITH(security_barrier=true) AS
SELECT *,revenue-cost gross_profit,revenue-cost-expense operating_profit,
(revenue-cost)/nullif(revenue,0) gross_margin
FROM dws.monthly_finance WHERE organization_id=identity.organization();
-- No login is provisioned automatically. Operator creates distinct SCRAM logins,
-- grants finagent_reader, and inserts the login->organization mapping as owner.
-- session_user survives SET ROLE; a custom GUC is never an identity source.

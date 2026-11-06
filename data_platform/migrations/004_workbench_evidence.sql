CREATE TABLE IF NOT EXISTS ods.workbench_evidence(
 organization_id text NOT NULL,batch_id uuid NOT NULL,document_id text NOT NULL,
 document_kind text NOT NULL CHECK(document_kind IN ('invoice','reimbursement','risk')),
 source_sha256 text NOT NULL CHECK(source_sha256 ~ '^[a-f0-9]{64}$'),
 original_content bytea NOT NULL,original_payload jsonb NOT NULL,
 validation_status text NOT NULL CHECK(validation_status IN ('accepted','quarantined')),
 quality_errors jsonb NOT NULL CHECK(jsonb_typeof(quality_errors)='array'),
 schema_version text NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(organization_id,document_id,source_sha256),
 UNIQUE(organization_id,batch_id,document_id,source_sha256),
 FOREIGN KEY(organization_id,batch_id) REFERENCES metadata.data_batch(organization_id,id),
 CHECK(validation_status<>'quarantined' OR jsonb_array_length(quality_errors)>0)
);
CREATE TABLE IF NOT EXISTS metadata.workbench_risk_evidence(
 organization_id text NOT NULL,batch_id uuid NOT NULL,document_id text NOT NULL,
 source_sha256 text NOT NULL,risk_id text NOT NULL,rule_version text NOT NULL,
 evidence jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),
 PRIMARY KEY(organization_id,risk_id,document_id,source_sha256,rule_version),
 FOREIGN KEY(organization_id,batch_id,document_id,source_sha256)
 REFERENCES ods.workbench_evidence(organization_id,batch_id,document_id,source_sha256)
);
CREATE OR REPLACE FUNCTION ods.preserve_workbench_original() RETURNS trigger
LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Original evidence is append only' USING ERRCODE='23514'; END $$;
DROP TRIGGER IF EXISTS preserve_original ON ods.workbench_evidence;
CREATE TRIGGER preserve_original BEFORE UPDATE OR DELETE ON ods.workbench_evidence
FOR EACH ROW EXECUTE FUNCTION ods.preserve_workbench_original();
REVOKE ALL ON ods.workbench_evidence,metadata.workbench_risk_evidence FROM PUBLIC,finagent_reader;

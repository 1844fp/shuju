CREATE TABLE IF NOT EXISTS metadata.erp_snapshot (
 organization_id text NOT NULL, batch_id uuid NOT NULL, source_sha256 text NOT NULL,
 source_name text NOT NULL, original_content bytea NOT NULL, cleaning_metadata jsonb NOT NULL,
 PRIMARY KEY(organization_id,batch_id),
 FOREIGN KEY(organization_id,batch_id) REFERENCES metadata.data_batch(organization_id,id)
);
CREATE TABLE IF NOT EXISTS ods.erp_source_row (
 organization_id text NOT NULL, batch_id uuid NOT NULL, source_row_number integer NOT NULL,
 original_payload jsonb NOT NULL, normalized_payload jsonb, row_status text NOT NULL,
 quality_errors jsonb NOT NULL, cleaning_changes jsonb NOT NULL,
 PRIMARY KEY(organization_id,batch_id,source_row_number),
 FOREIGN KEY(organization_id,batch_id) REFERENCES metadata.data_batch(organization_id,id)
);
REVOKE ALL ON metadata.erp_snapshot, ods.erp_source_row FROM PUBLIC;

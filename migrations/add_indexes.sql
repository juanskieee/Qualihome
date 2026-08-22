-- ============================================================
-- QUALIHOME — Performance Index Migration (MySQL 8.4 / Aiven)
--
-- NOTE: MySQL does NOT support `ADD INDEX IF NOT EXISTS`
-- (that is MariaDB syntax). These are plain DDL statements —
-- run ONCE. If any statement reports "Duplicate key name",
-- that index already exists: safe to ignore / skip.
--
-- Run against the production database:
--   mysql --host=<DB_HOST> --port=3306 --user=<DB_USER> -p \
--         --ssl-ca=aiven-ca.pem <DB_NAME> < migrations/add_indexes.sql
-- ============================================================

-- ── CRITICAL ────────────────────────────────────────────────

-- Dashboard/landing browse queries:
--   WHERE status='available' AND approval_status IN ('approved', NULL)
--   ORDER BY created_at DESC
ALTER TABLE properties
    ADD INDEX idx_properties_status_approval_created (status, approval_status, created_at);

-- All "latest N assessments per client" sorts.
ALTER TABLE qualification_results
    ADD INDEX idx_qr_user_created (user_id, created_at);

-- Prefix index for AUTO_SYNC dedupe LIKE scans.
ALTER TABLE training_data
    ADD INDEX idx_td_notes (notes(64));

-- ── HIGH ────────────────────────────────────────────────────

-- Agent/client sold-listings sorted by sold_at DESC.
ALTER TABLE property_sales
    ADD INDEX idx_ps_agent_sold (agent_id, sold_at);

ALTER TABLE property_sales
    ADD INDEX idx_ps_client_sold (client_id, sold_at);

-- Agent notification feeds + unread counts.
ALTER TABLE agent_notifications
    ADD INDEX idx_an_agent_type_read_created (agent_id, event_type, is_read, created_at);

-- Client trip feed, agent trip joins, bulk read-receipt update.
ALTER TABLE tripping_requests
    ADD INDEX idx_trip_client_created (client_id, created_at);

ALTER TABLE tripping_requests
    ADD INDEX idx_trip_property_status_read (property_id, status, notification_read);

-- ── MEDIUM ──────────────────────────────────────────────────

-- Composite matching availability lookups (old single-column indexes
-- are left in place — harmless, avoids destructive statements).
ALTER TABLE agent_availability
    ADD INDEX idx_aa_agent_date (agent_id, available_date);

ALTER TABLE agent_availability
    ADD INDEX idx_aa_date (available_date);

ALTER TABLE property_pricing_detail_requests
    ADD INDEX idx_ppdr_status (status);

ALTER TABLE property_pricing_detail_request_history
    ADD INDEX idx_pdrh_request_status (request_id, status);

ALTER TABLE property_pricing_detail_request_history
    ADD INDEX idx_pdrh_property_requested (property_id, requested_at);

ALTER TABLE users
    ADD INDEX idx_users_role_active_created (role, is_active, created_at);

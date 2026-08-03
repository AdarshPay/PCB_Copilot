-- PCB Copilot initial schema (prototype)
-- Relational storage for designs, revisions, findings, and provenance.
-- Graph projections are derived in application code (NetworkX), not Neo4j.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

CREATE TABLE IF NOT EXISTS projects (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS design_revisions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id      UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    design_id       TEXT NOT NULL,
    revision        TEXT NOT NULL,
    source_tool     TEXT NOT NULL DEFAULT 'kicad',
    source_version  TEXT,
    ir_json         JSONB NOT NULL,
    object_key      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (project_id, design_id, revision)
);

CREATE TABLE IF NOT EXISTS findings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    revision_id     UUID NOT NULL REFERENCES design_revisions(id) ON DELETE CASCADE,
    rule_id         TEXT NOT NULL,
    severity        TEXT NOT NULL,
    objects         JSONB NOT NULL DEFAULT '[]'::jsonb,
    explanation     TEXT NOT NULL,
    evidence_refs   JSONB NOT NULL DEFAULT '[]'::jsonb,
    confidence      DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    remediation     JSONB NOT NULL DEFAULT '[]'::jsonb,
    source          TEXT NOT NULL DEFAULT 'deterministic',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS operations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    revision_id     UUID NOT NULL REFERENCES design_revisions(id) ON DELETE CASCADE,
    op_type         TEXT NOT NULL,
    target          TEXT NOT NULL,
    payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
    risk_tier       TEXT NOT NULL DEFAULT 'medium',
    confidence      DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    rollback        JSONB NOT NULL DEFAULT '{}'::jsonb,
    status          TEXT NOT NULL DEFAULT 'proposed',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS evidence_documents (
    id              TEXT PRIMARY KEY,
    kind            TEXT NOT NULL,
    title           TEXT,
    uri             TEXT,
    page            INTEGER,
    excerpt         TEXT,
    embedding       vector(1536),
    metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS rule_definitions (
    rule_id         TEXT PRIMARY KEY,
    pack            TEXT NOT NULL DEFAULT 'v0',
    category        TEXT NOT NULL,
    description     TEXT NOT NULL,
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    version         TEXT NOT NULL DEFAULT '0.1.0'
);

CREATE INDEX IF NOT EXISTS idx_findings_revision ON findings(revision_id);
CREATE INDEX IF NOT EXISTS idx_findings_rule ON findings(rule_id);
CREATE INDEX IF NOT EXISTS idx_design_revisions_project ON design_revisions(project_id);

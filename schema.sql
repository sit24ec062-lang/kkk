-- ================================================================
-- PM-SURAJ SEVA · NO WRONG DOOR — Beneficiary Journey Intelligence
-- SIH 2026 · PS 26092 · MoSJE / NSFDC ecosystem · Sandbox v2.0
-- ================================================================
PRAGMA foreign_keys = ON;

-- ---------- Users (applicant / officer / admin) ----------
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    mobile        TEXT UNIQUE NOT NULL,
    password      TEXT NOT NULL DEFAULT 'demo1234',
    role          TEXT NOT NULL DEFAULT 'applicant',   -- applicant / officer / admin
    org           TEXT DEFAULT '',                      -- officer's org (TAHDCO / bank)
    district      TEXT NOT NULL,
    is_sc         INTEGER NOT NULL DEFAULT 1,
    is_woman      INTEGER NOT NULL DEFAULT 0,
    family_income INTEGER,
    language      TEXT DEFAULT 'ta',
    created_at    TEXT DEFAULT (datetime('now'))
);

-- ---------- Applications (mirrors PM-SURAJ handoff) ----------
CREATE TABLE IF NOT EXISTS applications (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    app_no       TEXT UNIQUE NOT NULL,          -- PMS2026-TN-XXXXXX
    user_id      INTEGER REFERENCES users(id),
    fdc          TEXT NOT NULL DEFAULT 'NSFDC', -- NSFDC / NBCFDC / NSKFDC
    scheme_id    TEXT NOT NULL,
    amount       INTEGER NOT NULL,
    project_cost INTEGER,
    purpose      TEXT DEFAULT 'business',
    stage        INTEGER NOT NULL DEFAULT 1,    -- 1..11 (see STAGES in seed)
    status       TEXT NOT NULL DEFAULT 'IN_PROCESS', -- IN_PROCESS / QUERY_RAISED / SANCTIONED / DISBURSED / CLOSED
    partner_id   INTEGER REFERENCES partners(id),
    created_at   TEXT DEFAULT (datetime('now')),
    updated_at   TEXT DEFAULT (datetime('now'))
);

-- ---------- Status timeline (process transparency engine) ----------
CREATE TABLE IF NOT EXISTS status_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id     INTEGER REFERENCES applications(id),
    stage      INTEGER NOT NULL,
    stage_key  TEXT NOT NULL,
    actor      TEXT NOT NULL,          -- SYSTEM / APPLICANT / TAHDCO / BANK_OFFICER / CP
    note       TEXT NOT NULL DEFAULT '',
    days_taken INTEGER DEFAULT 0,      -- days this stage took (SLA measurement)
    created_at TEXT DEFAULT (datetime('now'))
);

-- ---------- Query Resolution Engine ----------
CREATE TABLE IF NOT EXISTS queries (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id         INTEGER REFERENCES applications(id),
    raised_by      TEXT NOT NULL,       -- OFFICER name / org
    category       TEXT NOT NULL,       -- DOCUMENT / DATA_MISMATCH / ELIGIBILITY / FIELD / OTHER
    title          TEXT NOT NULL,
    detail         TEXT NOT NULL,
    action_by      TEXT NOT NULL DEFAULT 'APPLICANT',  -- who must act
    blocking       INTEGER DEFAULT 1,   -- 1 = blocks progression
    status         TEXT NOT NULL DEFAULT 'OPEN',       -- OPEN / RESOLVED
    resolution     TEXT DEFAULT '',
    created_at     TEXT DEFAULT (datetime('now')),
    resolved_at    TEXT
);

-- ---------- Channel partners (grounded: TAHDCO + PSB/RRB/MFI) ----------
CREATE TABLE IF NOT EXISTS partners (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    ptype         TEXT NOT NULL,        -- SCA / PSB / RRB / MFI / NBFC
    fdc           TEXT NOT NULL DEFAULT 'NSFDC',
    district      TEXT NOT NULL,
    block         TEXT DEFAULT '',
    schemes       TEXT NOT NULL DEFAULT '',
    address       TEXT NOT NULL DEFAULT '',
    contact       TEXT DEFAULT '',
    last_verified TEXT NOT NULL
);

-- ---------- Documents on file ----------
CREATE TABLE IF NOT EXISTS documents (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER REFERENCES users(id),
    app_id     INTEGER REFERENCES applications(id),
    doc_type   TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'ON_FILE',  -- REQUIRED / ON_FILE / VERIFIED / REJECTED
    note       TEXT DEFAULT '',
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, app_id, doc_type)
);

-- ---------- Post-disbursement outcome tracking ----------
CREATE TABLE IF NOT EXISTS outcomes (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    app_id           INTEGER REFERENCES applications(id),
    disbursed_amount INTEGER,
    business_started INTEGER DEFAULT 0,
    monthly_income   INTEGER,
    repayment_status TEXT DEFAULT 'ON_TIME',  -- ON_TIME / DUE / OVERDUE
    monitored_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS journeys (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,
    ref     TEXT UNIQUE NOT NULL,
    app_id  INTEGER REFERENCES applications(id),
    payload TEXT
);

CREATE INDEX IF NOT EXISTS idx_app_user    ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_events_app  ON status_events(app_id);
CREATE INDEX IF NOT EXISTS idx_queries_app ON queries(app_id);
CREATE INDEX IF NOT EXISTS idx_partners_d  ON partners(district);
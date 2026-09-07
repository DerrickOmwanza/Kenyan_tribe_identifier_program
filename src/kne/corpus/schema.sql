-- Kenya Name Engine corpus store schema.
-- schema_version is tracked in corpus_meta; bump it in build.py when this changes.

PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
    source_id   TEXT PRIMARY KEY,
    filename    TEXT NOT NULL,
    sha256      TEXT NOT NULL,
    row_count   INTEGER NOT NULL,
    ingested_at TEXT NOT NULL,
    tool_version TEXT NOT NULL,
    hash_verified INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS records (
    record_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL REFERENCES sources(source_id) ON DELETE CASCADE,
    row_index INTEGER NOT NULL,
    fname_raw TEXT,
    mname_raw TEXT,
    sname_raw TEXT,
    tribe_raw TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS records_source_idx ON records(source_id);
CREATE INDEX IF NOT EXISTS records_sname_idx ON records(sname_raw);

-- Aggregated single-token observations: how often a normalized token appears in a
-- given name position for each verbatim tribe label.
CREATE TABLE IF NOT EXISTS name_observations (
    token    TEXT NOT NULL,
    position TEXT NOT NULL CHECK (position IN ('fname', 'mname', 'sname')),
    tribe    TEXT NOT NULL,
    count    INTEGER NOT NULL,
    PRIMARY KEY (token, position, tribe)
) WITHOUT ROWID;

-- Aggregated multi-token combination observations.
-- combo_type in ('fname_sname', 'mname_sname', 'fname_mname_sname').
-- token_key is the normalized member tokens joined with '|'.
CREATE TABLE IF NOT EXISTS combo_observations (
    combo_type TEXT NOT NULL,
    token_key  TEXT NOT NULL,
    tribe      TEXT NOT NULL,
    count      INTEGER NOT NULL,
    PRIMARY KEY (combo_type, token_key, tribe)
) WITHOUT ROWID;

-- Derived per-(token, position) reference view. Rebuilt from scratch by build.py.
CREATE TABLE IF NOT EXISTS token_reference (
    token          TEXT NOT NULL,
    position       TEXT NOT NULL,
    support        INTEGER NOT NULL,
    distinct_tribes INTEGER NOT NULL,
    top_tribe      TEXT NOT NULL,
    top_share      REAL NOT NULL,
    entropy        REAL NOT NULL,
    dist_json      TEXT NOT NULL,
    PRIMARY KEY (token, position)
) WITHOUT ROWID;

-- Derived per-(combo_type, token_key) reference view, mirrors token_reference.
-- Rebuilt from scratch by build.py, filtered to support >= combo_min_support.
CREATE TABLE IF NOT EXISTS combo_reference (
    combo_type     TEXT NOT NULL,
    token_key      TEXT NOT NULL,
    support        INTEGER NOT NULL,
    distinct_tribes INTEGER NOT NULL,
    top_tribe      TEXT NOT NULL,
    top_share      REAL NOT NULL,
    entropy        REAL NOT NULL,
    dist_json      TEXT NOT NULL,
    PRIMARY KEY (combo_type, token_key)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS corpus_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

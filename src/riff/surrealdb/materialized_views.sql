-- ============================================================================
-- Materialized Views for Session State (Phase 6B)
-- ============================================================================
-- Purpose: Cache "current state" rebuilt from immutable repair events
--
-- Design Philosophy:
--   - repairs_events is SOURCE OF TRUTH (immutable, append-only)
--   - sessions_materialized is CACHE (mutable, rebuild from events)
--   - Materialized views provide fast queries without replaying events
--   - Can be dropped and rebuilt anytime from event log
--
-- Key Concepts:
--   - Materialization: Process of computing current state from events
--   - Rebuild: Discard cache and recompute from event log
--   - Incremental update: Apply new events to existing cache
--   - Validation: Verify cache matches event replay
-- ============================================================================

-- ----------------------------------------------------------------------------
-- TABLE: sessions_materialized (CACHED CURRENT STATE)
-- ----------------------------------------------------------------------------
-- This table represents the "current state" of all sessions after applying
-- all repair events. Unlike repairs_events (immutable), this table is:
--   - MUTABLE: Can be updated when new events arrive
--   - REBUILDABLE: Can be dropped and recreated from repairs_events
--   - CACHED: Optimized for fast queries (avoid replaying events)
--
-- Rebuild Strategy:
--   1. Full rebuild: DROP TABLE + replay all events (expensive)
--   2. Incremental: Apply only new events since last materialization
--   3. Validation: Periodically rebuild and compare for drift detection

DEFINE TABLE sessions_materialized SCHEMAFULL;

-- Session Identity
DEFINE FIELD session_id ON TABLE sessions_materialized TYPE string
    ASSERT $value != NONE AND string::len($value) > 0;

-- Message Parent Mappings (Current State)
DEFINE FIELD message_parents ON TABLE sessions_materialized TYPE object;
    -- Structure:
    -- {
    --   "msg-uuid-1": "parent-uuid-1",
    --   "msg-uuid-2": "parent-uuid-2",
    --   "msg-uuid-3": null  // root message
    -- }
    -- This represents the CURRENT parent for each message after all repairs

-- Repair Statistics
DEFINE FIELD total_repairs ON TABLE sessions_materialized TYPE int DEFAULT 0
    ASSERT $value >= 0;
    -- Total number of repair events (including reverted)

DEFINE FIELD active_repairs ON TABLE sessions_materialized TYPE int DEFAULT 0
    ASSERT $value >= 0;
    -- Number of currently active repairs (excluding reverted)

DEFINE FIELD reverted_repairs ON TABLE sessions_materialized TYPE int DEFAULT 0
    ASSERT $value >= 0;
    -- Number of repairs that were reverted

-- Materialization Metadata
DEFINE FIELD last_event_id ON TABLE sessions_materialized TYPE option<string>;
    -- Event ID of last processed event (for incremental updates)

DEFINE FIELD last_event_timestamp ON TABLE sessions_materialized TYPE option<datetime>;
    -- Timestamp of last processed event

DEFINE FIELD materialized_at ON TABLE sessions_materialized TYPE datetime
    ASSERT $value != NONE;
    -- When this materialized view was last rebuilt/updated

DEFINE FIELD event_count_at_materialization ON TABLE sessions_materialized TYPE int DEFAULT 0
    ASSERT $value >= 0;
    -- How many events were processed to build this view

-- Integrity Validation
DEFINE FIELD materialization_digest ON TABLE sessions_materialized TYPE string
    ASSERT $value != NONE AND string::len($value) == 64;
    -- SHA256 hash of all event_ids included in this materialization
    -- Used to detect if event log changed since materialization

DEFINE FIELD is_stale ON TABLE sessions_materialized TYPE bool DEFAULT false;
    -- Flag indicating view needs rebuild (set when new events arrive)

DEFINE FIELD drift_detected ON TABLE sessions_materialized TYPE bool DEFAULT false;
    -- Flag indicating mismatch between cache and event replay

-- Performance Metrics
DEFINE FIELD rebuild_duration_ms ON TABLE sessions_materialized TYPE int DEFAULT 0;
    -- How long it took to rebuild this view (milliseconds)

-- ----------------------------------------------------------------------------
-- INDEXES
-- ----------------------------------------------------------------------------

-- Primary lookup by session_id
DEFINE INDEX session_id_idx ON TABLE sessions_materialized COLUMNS session_id UNIQUE;

-- Stale views that need rebuild
DEFINE INDEX stale_views_idx ON TABLE sessions_materialized COLUMNS is_stale;

-- Drift detection queries
DEFINE INDEX drift_idx ON TABLE sessions_materialized COLUMNS drift_detected;

-- Materialization age queries
DEFINE INDEX materialized_at_idx ON TABLE sessions_materialized COLUMNS materialized_at;

-- ----------------------------------------------------------------------------
-- EXAMPLE QUERIES: Materialized View Operations
-- ----------------------------------------------------------------------------

-- Query: Get current parent mappings for a session (FAST - no event replay)
-- SELECT message_parents FROM sessions_materialized
-- WHERE session_id = $session_id;

-- Query: Check if materialized view is up-to-date
-- SELECT
--     session_id,
--     is_stale,
--     drift_detected,
--     materialized_at,
--     time::unix(time::now()) - time::unix(materialized_at) as age_seconds
-- FROM sessions_materialized
-- WHERE session_id = $session_id;

-- Query: Find sessions that need rebuild (stale or drift detected)
-- SELECT
--     session_id,
--     is_stale,
--     drift_detected,
--     materialized_at,
--     event_count_at_materialization
-- FROM sessions_materialized
-- WHERE is_stale = true OR drift_detected = true
-- ORDER BY materialized_at ASC
-- LIMIT 10;

-- Query: Compare materialized view with event replay (validation)
-- WITH
--   -- Get materialized state
--   materialized AS (
--     SELECT message_parents FROM sessions_materialized
--     WHERE session_id = $session_id
--   ),
--   -- Replay events to compute current state
--   replayed AS (
--     SELECT
--       message_id,
--       new_parent_uuid
--     FROM repairs_events
--     WHERE session_id = $session_id
--       AND is_reverted = false
--     ORDER BY timestamp ASC
--   )
-- SELECT
--   materialized.*,
--   replayed.*,
--   materialized.message_parents == replayed.parents as matches
-- FROM materialized, replayed;

-- Query: Performance metrics for materializations
-- SELECT
--     session_id,
--     event_count_at_materialization,
--     rebuild_duration_ms,
--     rebuild_duration_ms / event_count_at_materialization as ms_per_event
-- FROM sessions_materialized
-- ORDER BY rebuild_duration_ms DESC
-- LIMIT 20;

-- Query: Materialization age distribution
-- SELECT
--     CASE
--         WHEN time::unix(time::now()) - time::unix(materialized_at) < 3600
--             THEN 'fresh (<1h)'
--         WHEN time::unix(time::now()) - time::unix(materialized_at) < 86400
--             THEN 'recent (<1d)'
--         WHEN time::unix(time::now()) - time::unix(materialized_at) < 604800
--             THEN 'old (<1w)'
--         ELSE 'stale (>1w)'
--     END as age_category,
--     COUNT() as session_count
-- FROM sessions_materialized
-- GROUP BY age_category;

-- ============================================================================
-- REBUILD PROCEDURES (Python Implementation)
-- ============================================================================

-- Note: SurrealDB does not have stored procedures. Rebuild logic must be
-- implemented in Python. See repair_events_utils.py for implementation.
--
-- Rebuild Strategy:
--
-- 1. FULL REBUILD (from scratch):
--    a. Fetch all non-reverted events for session
--    b. Sort by timestamp ASC
--    c. Apply each event to build message_parents dict
--    d. Compute statistics (total_repairs, active_repairs, etc.)
--    e. Generate materialization_digest (SHA256 of all event_ids)
--    f. UPDATE or INSERT sessions_materialized
--
-- 2. INCREMENTAL UPDATE (append new events):
--    a. Fetch last_event_id from sessions_materialized
--    b. Query repairs_events WHERE timestamp > last_event_timestamp
--    c. Apply new events to existing message_parents
--    d. Update statistics and metadata
--    e. UPDATE sessions_materialized
--
-- 3. VALIDATION (detect drift):
--    a. Full rebuild to temporary structure
--    b. Compare with sessions_materialized
--    c. If mismatch: Set drift_detected = true
--    d. Alert operator for manual investigation
--
-- 4. CLEANUP (mark stale):
--    - After new event inserted: UPDATE is_stale = true
--    - Background job rebuilds stale views periodically
--
-- Example Python code:
--
-- def rebuild_materialized_view(session_id: str) -> None:
--     """Full rebuild of materialized view from events."""
--     start_time = time.time()
--
--     # Fetch all active events
--     events = db.query("""
--         SELECT * FROM repairs_events
--         WHERE session_id = $session_id
--           AND is_reverted = false
--         ORDER BY timestamp ASC
--     """, {"session_id": session_id})
--
--     # Build message_parents dict
--     message_parents = {}
--     for event in events:
--         message_parents[event.message_id] = event.new_parent_uuid
--
--     # Compute statistics
--     total_repairs = db.query("""
--         SELECT COUNT() FROM repairs_events
--         WHERE session_id = $session_id
--     """).result
--
--     active_repairs = len(events)
--     reverted_repairs = total_repairs - active_repairs
--
--     # Generate digest (SHA256 of sorted event_ids)
--     event_ids = sorted([e.event_id for e in events])
--     digest = hashlib.sha256("".join(event_ids).encode()).hexdigest()
--
--     # Update materialized view
--     db.query("""
--         UPDATE sessions_materialized
--         SET message_parents = $message_parents,
--             total_repairs = $total_repairs,
--             active_repairs = $active_repairs,
--             reverted_repairs = $reverted_repairs,
--             last_event_id = $last_event_id,
--             last_event_timestamp = $last_timestamp,
--             materialized_at = time::now(),
--             event_count_at_materialization = $event_count,
--             materialization_digest = $digest,
--             is_stale = false,
--             rebuild_duration_ms = $duration_ms
--         WHERE session_id = $session_id
--     """, {
--         "session_id": session_id,
--         "message_parents": message_parents,
--         "total_repairs": total_repairs,
--         "active_repairs": active_repairs,
--         "reverted_repairs": reverted_repairs,
--         "last_event_id": events[-1].event_id if events else None,
--         "last_timestamp": events[-1].timestamp if events else None,
--         "event_count": len(events),
--         "digest": digest,
--         "duration_ms": int((time.time() - start_time) * 1000)
--     })
--
-- def validate_materialized_view(session_id: str) -> bool:
--     """Validate materialized view matches event replay."""
--     # Get materialized state
--     materialized = db.query("""
--         SELECT message_parents FROM sessions_materialized
--         WHERE session_id = $session_id
--     """).result
--
--     # Rebuild from events
--     replayed = replay_repair_events(session_id)
--
--     # Compare
--     matches = (materialized.message_parents == replayed.message_parents)
--
--     if not matches:
--         # Mark drift
--         db.query("""
--             UPDATE sessions_materialized
--             SET drift_detected = true
--             WHERE session_id = $session_id
--         """)
--         logger.error(f"Drift detected in session {session_id}")
--
--     return matches

-- ============================================================================
-- BACKGROUND JOBS (Scheduled Maintenance)
-- ============================================================================

-- Note: Implement these as Python scheduled jobs (e.g., cron, APScheduler)
--
-- 1. Rebuild Stale Views (every 5 minutes):
--    - Find all sessions_materialized WHERE is_stale = true
--    - Rebuild each using incremental update
--    - Limit to 10 per run to avoid overwhelming system
--
-- 2. Validate Random Sample (every hour):
--    - Select 5 random sessions
--    - Run full validation (compare materialized vs replay)
--    - Alert if drift detected
--
-- 3. Cleanup Old Materializations (daily):
--    - Find sessions with no new events in 30 days
--    - Archive to cold storage
--    - Optionally: Delete materialized view (rebuild on demand)
--
-- 4. Integrity Check (weekly):
--    - Validate all materialization_digest values
--    - Verify event_count_at_materialization matches actual event count
--    - Alert on mismatches

-- ============================================================================
-- MIGRATION NOTES
-- ============================================================================
--
-- Initial Setup:
-- 1. Run: surreal import --conn http://localhost:8000 \
--         --user root --pass root --ns nabi --db conversations \
--         materialized_views.sql
--
-- 2. Verify: SELECT * FROM information_schema.tables
--            WHERE name = 'sessions_materialized';
--
-- Populate Initial Materializations:
-- 1. For each session in sessions table:
--    - Run rebuild_materialized_view(session_id)
--    - Verify is_stale = false
--
-- Monitor Health:
-- - Dashboard: Count of stale/drift_detected views
-- - Alert: Any drift_detected = true
-- - Metrics: Average rebuild_duration_ms by event_count
--
-- Troubleshooting:
-- - If drift detected: Compare materialized vs replayed manually
-- - If rebuild too slow: Consider partitioning events by session_id
-- - If stale views accumulate: Check background job is running
--
-- ============================================================================

-- ============================================================================
-- SurrealDB Schema for Immutable Repair Events (Phase 6B)
-- ============================================================================
-- Purpose: Event sourcing for conversation repair operations
--
-- Design Philosophy:
--   - APPEND-ONLY: Events can only be INSERTed, never UPDATEd or DELETEd
--   - IMMUTABLE: Once written, events are permanent audit trail
--   - REPLAYABLE: Can rebuild state by replaying event sequence
--   - AUDITABLE: Full provenance of all repair decisions
--
-- Key Concepts:
--   - repairs_events table: Immutable log of all repair operations
--   - sessions_materialized: Cached "current state" rebuilt from events
--   - Event sourcing prevents cascading corruption and enables time-travel
-- ============================================================================

-- ----------------------------------------------------------------------------
-- TABLE: repairs_events (IMMUTABLE EVENT LOG)
-- ----------------------------------------------------------------------------
-- This table is APPEND-ONLY. Once an event is written, it MUST never be:
--   - Updated (no UPDATE statements allowed)
--   - Deleted (no DELETE statements allowed)
--   - Modified (field values are immutable)
--
-- To "undo" a repair, create a NEW revert event with is_reverted=true
-- pointing to the original event_id. Never modify the original.
--
-- This ensures:
--   1. Complete audit trail (who repaired what, when, why)
--   2. Replay capability (rebuild any session state from events)
--   3. Integrity validation (detect if events were tampered)
--   4. Time-travel queries (state at any point in history)

DEFINE TABLE repairs_events SCHEMAFULL;

-- Core Fields
DEFINE FIELD event_id ON TABLE repairs_events TYPE string
    ASSERT $value != NONE AND string::len($value) > 0;

DEFINE FIELD session_id ON TABLE repairs_events TYPE string
    ASSERT $value != NONE AND string::len($value) > 0;

DEFINE FIELD timestamp ON TABLE repairs_events TYPE datetime
    ASSERT $value != NONE;

-- Repair Details
DEFINE FIELD message_id ON TABLE repairs_events TYPE string
    ASSERT $value != NONE AND string::len($value) > 0;

DEFINE FIELD old_parent_uuid ON TABLE repairs_events TYPE option<string>;

DEFINE FIELD new_parent_uuid ON TABLE repairs_events TYPE string
    ASSERT $value != NONE AND string::len($value) > 0;

-- Metadata
DEFINE FIELD operator ON TABLE repairs_events TYPE string
    ASSERT $value != NONE;
    -- Who performed the repair (e.g., "user:tryk", "agent:orchestrator-xyz", "system:auto-repair")

DEFINE FIELD reason ON TABLE repairs_events TYPE string
    ASSERT $value != NONE;
    -- Human-readable explanation (e.g., "semantic similarity", "timestamp proximity", "manual override")

DEFINE FIELD similarity_score ON TABLE repairs_events TYPE float DEFAULT 0.0
    ASSERT $value >= 0.0 AND $value <= 1.0;
    -- Confidence score from repair engine (0.0 = manual override, 1.0 = high confidence)

-- Validation & Status
DEFINE FIELD validation_passed ON TABLE repairs_events TYPE bool DEFAULT true;
    -- Whether repair passed validation checks (circular dependency, timestamp logic)

DEFINE FIELD is_reverted ON TABLE repairs_events TYPE bool DEFAULT false;
    -- Mark as reverted instead of deleting (preserves audit trail)

DEFINE FIELD reverts_event_id ON TABLE repairs_events TYPE option<string>;
    -- If this is a revert event, which event_id is being reversed

-- Integrity
DEFINE FIELD event_digest ON TABLE repairs_events TYPE string
    ASSERT $value != NONE AND string::len($value) == 64;
    -- SHA256 hash of event content for tamper detection
    -- Computed as: SHA256(event_id + session_id + timestamp + message_id + old_parent + new_parent)

DEFINE FIELD created_at ON TABLE repairs_events TYPE datetime
    ASSERT $value != NONE;
    -- System timestamp when event was persisted (vs. timestamp which is when repair occurred)

-- ----------------------------------------------------------------------------
-- INDEXES: Fast Queries and Integrity Checks
-- ----------------------------------------------------------------------------

-- Unique constraint: One event_id cannot be reused
DEFINE INDEX event_id_idx ON TABLE repairs_events COLUMNS event_id UNIQUE;

-- Session + timestamp: Replay events in order
DEFINE INDEX session_timestamp_idx ON TABLE repairs_events COLUMNS session_id, timestamp;

-- Message lookup: Find all repairs for a specific message
DEFINE INDEX message_id_idx ON TABLE repairs_events COLUMNS message_id;

-- Revert lookup: Find original event from revert
DEFINE INDEX reverts_event_idx ON TABLE repairs_events COLUMNS reverts_event_id;

-- Active repairs: Filter out reverted events
DEFINE INDEX active_repairs_idx ON TABLE repairs_events COLUMNS session_id, is_reverted;

-- Operator audit: Who performed repairs
DEFINE INDEX operator_idx ON TABLE repairs_events COLUMNS operator;

-- Timestamp range queries: Events within time window
DEFINE INDEX timestamp_idx ON TABLE repairs_events COLUMNS timestamp;

-- Integrity validation: Detect tampered events
DEFINE INDEX digest_idx ON TABLE repairs_events COLUMNS event_digest;

-- ----------------------------------------------------------------------------
-- RELATIONS: Link to Sessions
-- ----------------------------------------------------------------------------

-- Relation: repairs_events -> session
-- Links repair events to their parent session
-- Enables: "Get all repairs for this session"
DEFINE TABLE repairs_events_for_session SCHEMAFULL;
DEFINE FIELD in ON TABLE repairs_events_for_session TYPE record<repairs_events>;
DEFINE FIELD out ON TABLE repairs_events_for_session TYPE record<session>;
DEFINE INDEX repairs_events_for_session_in_idx ON TABLE repairs_events_for_session COLUMNS in;
DEFINE INDEX repairs_events_for_session_out_idx ON TABLE repairs_events_for_session COLUMNS out;

-- Relation: repairs_events -> message
-- Links repair events to the message being repaired
-- Enables: "Get repair history for this message"
DEFINE TABLE repairs_events_for_message SCHEMAFULL;
DEFINE FIELD in ON TABLE repairs_events_for_message TYPE record<repairs_events>;
DEFINE FIELD out ON TABLE repairs_events_for_message TYPE record<message>;
DEFINE INDEX repairs_events_for_message_in_idx ON TABLE repairs_events_for_message COLUMNS in;
DEFINE INDEX repairs_events_for_message_out_idx ON TABLE repairs_events_for_message COLUMNS out;

-- ----------------------------------------------------------------------------
-- IMMUTABILITY ENFORCEMENT (CRITICAL)
-- ----------------------------------------------------------------------------

-- Note: SurrealDB does not have built-in triggers like PostgreSQL.
-- Immutability must be enforced at the application layer:
--
-- 1. Python code MUST only INSERT, never UPDATE/DELETE
-- 2. Database permissions SHOULD restrict UPDATE/DELETE (if using auth)
-- 3. Integrity validation via event_digest SHA256 hash
--
-- Example enforcement in Python:
--   def write_repair_event(event: RepairEvent) -> bool:
--       # Only INSERT allowed
--       result = db.query("INSERT INTO repairs_events", event)
--       return result.is_ok()
--
--   def update_repair_event(event_id: str) -> None:
--       # FORBIDDEN - will raise exception
--       raise ImmutableEventError("Cannot modify repair events")
--
--   def delete_repair_event(event_id: str) -> None:
--       # FORBIDDEN - will raise exception
--       raise ImmutableEventError("Cannot delete repair events")
--
-- To "undo" a repair, create a revert event:
--   new_event = RepairEvent(
--       event_id=generate_uuid(),
--       is_reverted=True,
--       reverts_event_id=original_event.event_id,
--       # ... swap old_parent and new_parent to reverse repair
--   )

-- ============================================================================
-- EXAMPLE QUERIES
-- ============================================================================

-- Query: Get all active (non-reverted) repairs for a session
-- SELECT * FROM repairs_events
-- WHERE session_id = $session_id
--   AND is_reverted = false
-- ORDER BY timestamp ASC;

-- Query: Replay repair events to rebuild session state
-- SELECT
--     message_id,
--     new_parent_uuid as current_parent,
--     timestamp,
--     operator,
--     reason
-- FROM repairs_events
-- WHERE session_id = $session_id
--   AND is_reverted = false
-- ORDER BY timestamp ASC;

-- Query: Get repair history for a specific message (chronological)
-- SELECT * FROM repairs_events
-- WHERE message_id = $message_id
-- ORDER BY timestamp ASC;

-- Query: Find which events were reverted and who reverted them
-- SELECT
--     original.event_id as original_event,
--     original.message_id,
--     original.operator as original_operator,
--     revert.event_id as revert_event,
--     revert.operator as revert_operator,
--     revert.timestamp as revert_time
-- FROM repairs_events as original
-- INNER JOIN repairs_events as revert
--   ON revert.reverts_event_id = original.event_id
-- WHERE original.session_id = $session_id;

-- Query: Validate event integrity (detect tampering)
-- SELECT
--     event_id,
--     event_digest,
--     crypto::sha256(
--         string::concat(
--             event_id,
--             session_id,
--             <string>timestamp,
--             message_id,
--             old_parent_uuid OR "null",
--             new_parent_uuid
--         )
--     ) as computed_digest,
--     event_digest == computed_digest as is_valid
-- FROM repairs_events
-- WHERE session_id = $session_id;

-- Query: Count repairs by operator (audit who makes most repairs)
-- SELECT
--     operator,
--     COUNT() as repair_count,
--     math::avg(similarity_score) as avg_confidence
-- FROM repairs_events
-- WHERE session_id = $session_id
--   AND is_reverted = false
-- GROUP BY operator
-- ORDER BY repair_count DESC;

-- Query: Time-range query (repairs within specific window)
-- SELECT * FROM repairs_events
-- WHERE session_id = $session_id
--   AND timestamp >= $start_time
--   AND timestamp <= $end_time
-- ORDER BY timestamp ASC;

-- Query: Get full session state at specific point in time
-- SELECT
--     message_id,
--     new_parent_uuid as parent_at_time
-- FROM repairs_events
-- WHERE session_id = $session_id
--   AND timestamp <= $target_time
--   AND is_reverted = false
-- ORDER BY timestamp ASC;

-- Query: Identify messages with multiple repairs (unstable parentage)
-- SELECT
--     message_id,
--     COUNT() as repair_count,
--     array::group(operator) as operators,
--     array::group(reason) as reasons
-- FROM repairs_events
-- WHERE session_id = $session_id
--   AND is_reverted = false
-- GROUP BY message_id
-- HAVING COUNT() > 1
-- ORDER BY repair_count DESC;

-- Query: Validation failures (repairs that didn't pass checks)
-- SELECT * FROM repairs_events
-- WHERE session_id = $session_id
--   AND validation_passed = false
-- ORDER BY timestamp DESC;

-- ============================================================================
-- MIGRATION NOTES
-- ============================================================================
--
-- Initial Setup:
-- 1. Run: surreal import --conn http://localhost:8000 \
--         --user root --pass root --ns nabi --db conversations \
--         schema_events.sql
--
-- 2. Verify: SELECT * FROM information_schema.tables WHERE name = 'repairs_events';
--
-- Data Migration from JSONL backups:
-- 1. Parse existing .backup files in ~/.riff/backups/<session_id>/
-- 2. Convert to repair events with proper timestamps
-- 3. Bulk insert via Python client
-- 4. Validate integrity with SHA256 digests
--
-- Integrity Validation:
-- - Scheduled job: Verify all event_digest hashes match computed values
-- - Alert on mismatches (potential tampering or data corruption)
-- - Use for compliance/audit requirements
--
-- Performance Tuning:
-- - Partition by session_id for very large event logs (millions of repairs)
-- - Archive old events to cold storage after N days
-- - Consider secondary indexes on reason field for analytics
--
-- ============================================================================

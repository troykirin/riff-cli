-- ============================================================================
-- SurrealDB Schema for Conversation Storage (Phase 6B)
-- ============================================================================
-- Purpose: Store Claude conversation sessions with message threading,
--          temporal relationships, and corruption detection support
--
-- Design Philosophy:
--   - SCHEMAFULL for data integrity and validation
--   - FK references as strings (SurrealDB convention)
--   - Timestamps in ISO 8601 format
--   - corruption_score computed by Python, stored here
--   - Supports DAG-based conversation visualization
-- ============================================================================

-- ----------------------------------------------------------------------------
-- ANALYZERS: Text Search Configuration
-- ----------------------------------------------------------------------------

-- Define analyzer for full-text search on message content
-- Uses blank and class tokenizers with lowercase and English snowball stemming
DEFINE ANALYZER message_search TOKENIZERS blank, class FILTERS lowercase, snowball(english);

-- ----------------------------------------------------------------------------
-- TABLE: session
-- ----------------------------------------------------------------------------
-- Represents a single Claude conversation session
-- Tracks high-level metrics: message count, thread count, corruption score
-- Each session has a unique session_id (Claude UUID)

DEFINE TABLE session SCHEMAFULL;

-- Fields
DEFINE FIELD session_id ON TABLE session TYPE string
    ASSERT $value != NONE AND string::len($value) > 0;
DEFINE FIELD message_count ON TABLE session TYPE int DEFAULT 0
    ASSERT $value >= 0;
DEFINE FIELD thread_count ON TABLE session TYPE int DEFAULT 0
    ASSERT $value >= 0;
DEFINE FIELD corruption_score ON TABLE session TYPE float DEFAULT 0.0
    ASSERT $value >= 0.0 AND $value <= 1.0;
DEFINE FIELD session_hash ON TABLE session TYPE option<string>;
DEFINE FIELD last_updated ON TABLE session TYPE datetime;
DEFINE FIELD created_at ON TABLE session TYPE datetime;

-- Indexes
DEFINE INDEX session_id_idx ON TABLE session COLUMNS session_id UNIQUE;
DEFINE INDEX session_updated_idx ON TABLE session COLUMNS last_updated;
DEFINE INDEX session_hash_idx ON TABLE session COLUMNS session_hash;

-- ----------------------------------------------------------------------------
-- TABLE: thread
-- ----------------------------------------------------------------------------
-- Represents a logical conversation thread within a session
-- Types: main (primary conversation), side_discussion (tangent), orphaned (broken)
-- Tracks message count and semantic topic

DEFINE TABLE thread SCHEMAFULL;

-- Fields
DEFINE FIELD session_id ON TABLE thread TYPE string
    ASSERT $value != NONE AND string::len($value) > 0;
DEFINE FIELD thread_type ON TABLE thread TYPE string
    ASSERT $value IN ['main', 'side_discussion', 'orphaned'];
DEFINE FIELD message_count ON TABLE thread TYPE int DEFAULT 0
    ASSERT $value >= 0;
DEFINE FIELD topic ON TABLE thread TYPE option<string>;
DEFINE FIELD created_at ON TABLE thread TYPE datetime;

-- Indexes
DEFINE INDEX thread_session_idx ON TABLE thread COLUMNS session_id;
DEFINE INDEX thread_type_idx ON TABLE thread COLUMNS thread_type;
DEFINE INDEX thread_composite_idx ON TABLE thread COLUMNS session_id, thread_type;

-- ----------------------------------------------------------------------------
-- TABLE: message
-- ----------------------------------------------------------------------------
-- Represents a single message in a conversation
-- Supports parent-child relationships (DAG structure)
-- Tracks corruption metrics and orphan status

DEFINE TABLE message SCHEMAFULL;

-- Fields
DEFINE FIELD session_id ON TABLE message TYPE string
    ASSERT $value != NONE AND string::len($value) > 0;
DEFINE FIELD message_uuid ON TABLE message TYPE string
    ASSERT $value != NONE AND string::len($value) > 0;
DEFINE FIELD parent_uuid ON TABLE message TYPE option<string>;
DEFINE FIELD message_type ON TABLE message TYPE string
    ASSERT $value IN ['user', 'assistant', 'system'];
DEFINE FIELD role ON TABLE message TYPE string
    ASSERT $value IN ['user', 'assistant'];
DEFINE FIELD content ON TABLE message TYPE string
    ASSERT $value != NONE;
DEFINE FIELD timestamp ON TABLE message TYPE datetime;
DEFINE FIELD thread_id ON TABLE message TYPE option<string>;
DEFINE FIELD is_orphaned ON TABLE message TYPE bool DEFAULT false;
DEFINE FIELD corruption_score ON TABLE message TYPE float DEFAULT 0.0
    ASSERT $value >= 0.0 AND $value <= 1.0;
DEFINE FIELD created_at ON TABLE message TYPE datetime;

-- Indexes
DEFINE INDEX message_uuid_idx ON TABLE message COLUMNS message_uuid;
DEFINE INDEX message_session_idx ON TABLE message COLUMNS session_id;
DEFINE INDEX message_parent_idx ON TABLE message COLUMNS parent_uuid;
DEFINE INDEX message_thread_idx ON TABLE message COLUMNS thread_id;
DEFINE INDEX message_timestamp_idx ON TABLE message COLUMNS timestamp;
DEFINE INDEX message_orphaned_idx ON TABLE message COLUMNS is_orphaned;
DEFINE INDEX message_corruption_idx ON TABLE message COLUMNS corruption_score;
DEFINE INDEX message_composite_idx ON TABLE message COLUMNS session_id, timestamp;

-- Full-text search index on message content
DEFINE INDEX message_content_idx ON TABLE message COLUMNS content
    SEARCH ANALYZER message_search BM25(1.2, 0.75);

-- ----------------------------------------------------------------------------
-- TABLE: repair_event (Phase 6B - Immutable Event Log)
-- ----------------------------------------------------------------------------
-- Immutable append-only log of all repair operations
-- Tracks who made changes, when, and why (audit trail)
-- Never delete or update - only append

DEFINE TABLE repair_event SCHEMAFULL;

-- Fields
DEFINE FIELD session_id ON TABLE repair_event TYPE string
    ASSERT $value != NONE AND string::len($value) > 0;
DEFINE FIELD message_uuid ON TABLE repair_event TYPE string
    ASSERT $value != NONE AND string::len($value) > 0;
DEFINE FIELD event_type ON TABLE repair_event TYPE string
    ASSERT $value IN ['message_added', 'parent_repaired', 'content_updated', 'corruption_fixed'];
DEFINE FIELD operator ON TABLE repair_event TYPE string
    ASSERT $value != NONE AND string::len($value) > 0;
DEFINE FIELD timestamp ON TABLE repair_event TYPE datetime;
DEFINE FIELD reason ON TABLE repair_event TYPE string;
DEFINE FIELD old_value ON TABLE repair_event TYPE option<string>;
DEFINE FIELD new_value ON TABLE repair_event TYPE option<string>;

-- Indexes (append-only, so optimize for reads)
DEFINE INDEX repair_event_session_idx ON TABLE repair_event COLUMNS session_id;
DEFINE INDEX repair_event_message_idx ON TABLE repair_event COLUMNS message_uuid;
DEFINE INDEX repair_event_timestamp_idx ON TABLE repair_event COLUMNS timestamp;
DEFINE INDEX repair_event_operator_idx ON TABLE repair_event COLUMNS operator;
DEFINE INDEX repair_event_composite_idx ON TABLE repair_event COLUMNS session_id, timestamp;

-- ----------------------------------------------------------------------------
-- RELATIONS: Graph Edges
-- ----------------------------------------------------------------------------

-- Relation: message -> message (parent to child)
-- Represents the conversation flow DAG
-- A message can have zero (root) or one parent, and zero or many children
DEFINE TABLE message_parent_of SCHEMAFULL;
DEFINE FIELD in ON TABLE message_parent_of TYPE record<message>;
DEFINE FIELD out ON TABLE message_parent_of TYPE record<message>;
DEFINE INDEX message_parent_of_in_idx ON TABLE message_parent_of COLUMNS in;
DEFINE INDEX message_parent_of_out_idx ON TABLE message_parent_of COLUMNS out;

-- Relation: message -> thread
-- Links messages to their containing thread
-- Properties: position (order within thread)
DEFINE TABLE message_belongs_to_thread SCHEMAFULL;
DEFINE FIELD in ON TABLE message_belongs_to_thread TYPE record<message>;
DEFINE FIELD out ON TABLE message_belongs_to_thread TYPE record<thread>;
DEFINE FIELD position ON TABLE message_belongs_to_thread TYPE int
    ASSERT $value >= 0;
DEFINE INDEX message_belongs_to_thread_in_idx ON TABLE message_belongs_to_thread COLUMNS in;
DEFINE INDEX message_belongs_to_thread_out_idx ON TABLE message_belongs_to_thread COLUMNS out;

-- Relation: thread -> session
-- Links threads to their parent session
DEFINE TABLE thread_belongs_to_session SCHEMAFULL;
DEFINE FIELD in ON TABLE thread_belongs_to_session TYPE record<thread>;
DEFINE FIELD out ON TABLE thread_belongs_to_session TYPE record<session>;
DEFINE INDEX thread_belongs_to_session_in_idx ON TABLE thread_belongs_to_session COLUMNS in;
DEFINE INDEX thread_belongs_to_session_out_idx ON TABLE thread_belongs_to_session COLUMNS out;

-- Relation: session -> message (optional, for quick queries)
-- Direct link from session to all its messages
-- Can be used for fast session-wide queries without joining through thread
DEFINE TABLE session_contains_message SCHEMAFULL;
DEFINE FIELD in ON TABLE session_contains_message TYPE record<session>;
DEFINE FIELD out ON TABLE session_contains_message TYPE record<message>;
DEFINE INDEX session_contains_message_in_idx ON TABLE session_contains_message COLUMNS in;
DEFINE INDEX session_contains_message_out_idx ON TABLE session_contains_message COLUMNS out;

-- ============================================================================
-- EXAMPLE QUERIES (for reference)
-- ============================================================================

-- Query: Find all orphaned messages in a session
-- SELECT * FROM message
-- WHERE session_id = $session_id AND is_orphaned = true
-- ORDER BY timestamp DESC;

-- Query: Get session statistics
-- SELECT
--     session_id,
--     COUNT() as total_messages,
--     math::sum(is_orphaned) as orphaned_count,
--     math::avg(corruption_score) as avg_corruption
-- FROM message
-- WHERE session_id = $session_id
-- GROUP ALL;

-- Query: Find potential parent candidates for orphaned message
-- (Messages that occurred before the orphan timestamp)
-- SELECT * FROM message
-- WHERE session_id = $session_id
--   AND timestamp < $orphan_timestamp
--   AND is_orphaned = false
-- ORDER BY timestamp DESC
-- LIMIT 5;

-- Query: Get conversation thread with all messages in order
-- SELECT * FROM message
-- WHERE thread_id = $thread_id
-- ORDER BY timestamp ASC;

-- Query: Full-text search across all messages in session
-- SELECT * FROM message
-- WHERE session_id = $session_id
--   AND content @@ 'search terms'
-- ORDER BY timestamp DESC;

-- Query: Get message with parent-child relationships (graph traversal)
-- SELECT *,
--   <-message_parent_of<-message as children,
--   ->message_parent_of->message as parent
-- FROM message:$message_id;

-- Query: Get all threads in session with message counts
-- SELECT
--     id,
--     thread_type,
--     topic,
--     message_count,
--     created_at
-- FROM thread
-- WHERE session_id = $session_id
-- ORDER BY created_at ASC;

-- Query: Get messages with high corruption scores (prioritized for review)
-- SELECT * FROM message
-- WHERE session_id = $session_id
--   AND corruption_score > 0.5
-- ORDER BY corruption_score DESC, timestamp ASC
-- LIMIT 20;

-- Query: Get orphaned messages with potential parent candidates
-- SELECT
--     orphan.*,
--     (SELECT * FROM message
--      WHERE session_id = orphan.session_id
--        AND timestamp < orphan.timestamp
--        AND timestamp > time::unix(time::unix(orphan.timestamp) - 3600)
--      ORDER BY timestamp DESC
--      LIMIT 5) as parent_candidates
-- FROM message as orphan
-- WHERE orphan.session_id = $session_id
--   AND orphan.is_orphaned = true;

-- Query: Time-range query (messages in specific time window)
-- SELECT * FROM message
-- WHERE session_id = $session_id
--   AND timestamp >= $start_time
--   AND timestamp <= $end_time
-- ORDER BY timestamp ASC;

-- Query: Get thread topics for semantic analysis
-- SELECT thread_type, topic, message_count
-- FROM thread
-- WHERE session_id = $session_id
--   AND topic IS NOT NONE
-- ORDER BY message_count DESC;

-- ----------------------------------------------------------------------------
-- TABLE: repairs_events (Phase 6B: Immutable Event Log)
-- ----------------------------------------------------------------------------
-- Append-only log of all repair operations
-- Events are NEVER updated or deleted - provides full audit trail
-- Can replay events to reconstruct session state at any point in time

DEFINE TABLE repairs_events SCHEMAFULL;

-- Fields
DEFINE FIELD event_id ON TABLE repairs_events TYPE string
    ASSERT $value != NONE AND string::len($value) > 0;
DEFINE FIELD session_id ON TABLE repairs_events TYPE string
    ASSERT $value != NONE AND string::len($value) > 0;
DEFINE FIELD timestamp ON TABLE repairs_events TYPE datetime;
DEFINE FIELD operator ON TABLE repairs_events TYPE string
    ASSERT $value != NONE;
DEFINE FIELD message_id ON TABLE repairs_events TYPE string
    ASSERT $value != NONE AND string::len($value) > 0;
DEFINE FIELD old_parent_uuid ON TABLE repairs_events TYPE option<string>;
DEFINE FIELD new_parent_uuid ON TABLE repairs_events TYPE string
    ASSERT $value != NONE AND string::len($value) > 0;
DEFINE FIELD reason ON TABLE repairs_events TYPE string;
DEFINE FIELD validation_passed ON TABLE repairs_events TYPE bool DEFAULT true;

-- Indexes
DEFINE INDEX repairs_event_id_idx ON TABLE repairs_events COLUMNS event_id UNIQUE;
DEFINE INDEX repairs_session_idx ON TABLE repairs_events COLUMNS session_id;
DEFINE INDEX repairs_message_idx ON TABLE repairs_events COLUMNS message_id;
DEFINE INDEX repairs_timestamp_idx ON TABLE repairs_events COLUMNS timestamp;
DEFINE INDEX repairs_composite_idx ON TABLE repairs_events COLUMNS session_id, timestamp;

-- ----------------------------------------------------------------------------
-- TABLE: sessions_materialized (Phase 6B: Cached Materialized Views)
-- ----------------------------------------------------------------------------
-- Cached results of session materialization (JSONL + event replay)
-- Invalidated when new repair events are logged
-- Provides fast access to fully-repaired sessions

DEFINE TABLE sessions_materialized SCHEMAFULL;

-- Fields
DEFINE FIELD session_id ON TABLE sessions_materialized TYPE string
    ASSERT $value != NONE AND string::len($value) > 0;
DEFINE FIELD message_count ON TABLE sessions_materialized TYPE int DEFAULT 0
    ASSERT $value >= 0;
DEFINE FIELD thread_count ON TABLE sessions_materialized TYPE int DEFAULT 0
    ASSERT $value >= 0;
DEFINE FIELD corruption_score ON TABLE sessions_materialized TYPE float DEFAULT 0.0
    ASSERT $value >= 0.0 AND $value <= 1.0;
DEFINE FIELD cached_at ON TABLE sessions_materialized TYPE datetime;
DEFINE FIELD repair_events_applied ON TABLE sessions_materialized TYPE int DEFAULT 0
    ASSERT $value >= 0;

-- Indexes
DEFINE INDEX sessions_mat_id_idx ON TABLE sessions_materialized COLUMNS session_id UNIQUE;
DEFINE INDEX sessions_mat_cached_idx ON TABLE sessions_materialized COLUMNS cached_at;

-- ============================================================================
-- PHASE 6B QUERIES (for reference)
-- ============================================================================

-- Query: Log a repair event (immutable append)
-- CREATE repairs_events CONTENT {
--     event_id: $event_id,
--     session_id: $session_id,
--     timestamp: time::now(),
--     operator: $operator,
--     message_id: $message_id,
--     old_parent_uuid: $old_parent_uuid,
--     new_parent_uuid: $new_parent_uuid,
--     reason: $reason,
--     validation_passed: $validation_passed
-- };

-- Query: Get all repair events for a session (chronological)
-- SELECT * FROM repairs_events
-- WHERE session_id = $session_id
-- ORDER BY timestamp ASC;

-- Query: Get recent repair events (last 24 hours)
-- SELECT * FROM repairs_events
-- WHERE timestamp > time::unix(time::unix(time::now()) - 86400)
-- ORDER BY timestamp DESC;

-- Query: Invalidate materialized session cache
-- DELETE sessions_materialized WHERE session_id = $session_id;

-- Query: Check if materialized session is fresh
-- SELECT * FROM sessions_materialized
-- WHERE session_id = $session_id
--   AND cached_at > time::unix(time::unix(time::now()) - 300)
-- LIMIT 1;

-- Query: Count repair events by operator
-- SELECT operator, count() as repair_count
-- FROM repairs_events
-- GROUP BY operator
-- ORDER BY repair_count DESC;

-- Query: Find messages with most repairs
-- SELECT message_id, count() as repair_count
-- FROM repairs_events
-- GROUP BY message_id
-- ORDER BY repair_count DESC
-- LIMIT 10;

-- Query: Get repair history for specific message
-- SELECT * FROM repairs_events
-- WHERE message_id = $message_id
-- ORDER BY timestamp ASC;

-- ============================================================================
-- MIGRATION NOTES
-- ============================================================================
--
-- Initial Setup:
-- 1. Run this schema file: surreal import --conn http://localhost:8000
--                          --user root --pass root --ns nabi --db conversations
--                          schema.sql
--
-- 2. Verify tables: SELECT * FROM information_schema.tables;
--
-- 3. Verify indexes: SELECT * FROM information_schema.indexes;
--
-- Data Migration (from existing JSON/SQLite):
-- 1. Export sessions from old format
-- 2. Transform to SurrealDB records (see schema_utils.py)
-- 3. Bulk insert via Python client or HTTP API
--
-- Backup Strategy:
-- - Export: surreal export --conn http://localhost:8000 --ns nabi --db conversations backup.surql
-- - Import: surreal import --conn http://localhost:8000 --ns nabi --db conversations backup.surql
--
-- Performance Tuning:
-- - Monitor index usage with EXPLAIN
-- - Adjust BM25 parameters (1.2, 0.75) based on search quality
-- - Consider partitioning by session_id for very large datasets
--
-- ============================================================================

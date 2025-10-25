"""SurrealDB integration for conversation storage."""

from .schema_utils import (
    SCHEMA_DICT,
    get_schema_sql,
    validate_session_data,
    validate_message_data,
    validate_thread_data,
    prepare_session_record,
    prepare_message_record,
    prepare_thread_record,
    build_orphaned_messages_query,
    build_session_stats_query,
    build_parent_candidates_query,
    build_high_corruption_query,
    build_time_range_query,
    export_schema_as_dict,
    get_table_schema,
    get_relation_schema,
)

from .storage import (
    SurrealDBStorage,
    RepairEvent,
    SurrealDBConnectionError,
    RepairEventValidationError,
    SessionNotFoundError,
    MaterializationError,
    create_surrealdb_storage,
)

from .repair_provider import SurrealDBRepairProvider

__all__ = [
    # Schema utilities
    "SCHEMA_DICT",
    "get_schema_sql",
    "validate_session_data",
    "validate_message_data",
    "validate_thread_data",
    "prepare_session_record",
    "prepare_message_record",
    "prepare_thread_record",
    "build_orphaned_messages_query",
    "build_session_stats_query",
    "build_parent_candidates_query",
    "build_high_corruption_query",
    "build_time_range_query",
    "export_schema_as_dict",
    "get_table_schema",
    "get_relation_schema",
    # Storage classes (Phase 6B)
    "SurrealDBStorage",
    "RepairEvent",
    "SurrealDBConnectionError",
    "RepairEventValidationError",
    "SessionNotFoundError",
    "MaterializationError",
    "create_surrealdb_storage",
    # Repair provider (Phase 6B integration)
    "SurrealDBRepairProvider",
]

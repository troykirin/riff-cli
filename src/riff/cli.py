"""Unified riff CLI: search conversations + repair JSONL"""

from __future__ import annotations

import argparse
from pathlib import Path

from rich.console import Console

from .classic import cmd_scan, cmd_fix, cmd_tui
from .classic.commands.graph import cmd_graph as cmd_graph_classic
from .search import QdrantSearcher, ContentPreview
from .manifest_adapter import get_manifest_adapter
from .enhance import IntentEnhancer
from .graph import ConversationDAG, JSONLLoader
from .graph.visualizer import ConversationTreeVisualizer

console = Console()


def cmd_sync_surrealdb(args) -> int:
    """Sync session from JSONL to SurrealDB immutable event store"""
    try:
        import hashlib
        import json
        from datetime import datetime
        from pathlib import Path

        # Parse session ID
        session_id = args.session_id

        # Find JSONL file
        conversations_dir = Path.home() / ".claude" / "projects"
        jsonl_path = None

        # Check if it's a full path
        if "/" in session_id or "\\" in session_id:
            jsonl_path = Path(session_id)
            if not jsonl_path.exists():
                console.print(f"[red]Error: File not found: {jsonl_path}[/red]")
                return 1
            session_id = jsonl_path.stem
        else:
            # Search for session UUID
            for jsonl_file in conversations_dir.rglob(f"{session_id}*.jsonl"):
                jsonl_path = jsonl_file
                break

            if not jsonl_path:
                console.print(f"[red]Error: Session {session_id} not found[/red]")
                console.print(f"[dim]Searched in: {conversations_dir}[/dim]")
                return 1

        console.print(f"[cyan]Syncing session:[/cyan] {session_id}")
        console.print(f"[dim]Source: {jsonl_path}[/dim]\n")

        # Step 1: Load session from JSONL
        console.print("[cyan]Step 1:[/cyan] Loading from JSONL...")
        loader = JSONLLoader(jsonl_path.parent)
        messages = loader.load_messages(session_id)

        if not messages:
            console.print("[red]Error: No messages found in JSONL[/red]")
            return 1

        console.print(f"  ✓ Loaded {len(messages)} messages")

        # Calculate session hash
        session_data = json.dumps([{
            "uuid": m.uuid,
            "parent_uuid": m.parent_uuid,
            "type": m.type.value,
            "timestamp": m.timestamp,
        } for m in messages], sort_keys=True)
        session_hash = hashlib.sha256(session_data.encode()).hexdigest()[:16]

        console.print(f"  ✓ Session hash: {session_hash}")

        # Step 2: Check SurrealDB connection
        console.print("\n[cyan]Step 2:[/cyan] Connecting to SurrealDB...")
        try:
            from surrealdb import Surreal  # type: ignore[import-untyped]
        except ImportError:
            console.print("[red]Error: surrealdb package not installed[/red]")
            console.print("[yellow]Install with:[/yellow] uv pip install surrealdb")
            return 1

        # Initialize SurrealDB connection
        db_url = args.surrealdb_url or "ws://localhost:8000/rpc"
        db = Surreal(db_url)

        try:
            # Try async connection (this is a sync function, so we'll use a workaround)
            import asyncio

            async def sync_to_surrealdb():
                """Async helper for SurrealDB operations"""
                await db.connect()
                await db.signin({"user": "root", "pass": "root"})
                await db.use("nabi", "conversations")

                console.print(f"  ✓ Connected to {db_url}")

                # Step 3: Check if session exists
                console.print("\n[cyan]Step 3:[/cyan] Checking existing session...")

                result = await db.query(f"SELECT * FROM session WHERE session_id = '{session_id}'")
                existing_session = result[0]["result"] if result and result[0].get("result") else None

                if existing_session and len(existing_session) > 0:
                    existing_hash = existing_session[0].get("session_hash", "")
                    console.print(f"  • Found existing session (hash: {existing_hash})")

                    if existing_hash == session_hash and not args.force:
                        console.print("\n[green]✓ Session already up-to-date in SurrealDB[/green]")
                        console.print("[dim]Use --force to re-sync anyway[/dim]")
                        return 0
                else:
                    console.print("  • New session (not in SurrealDB)")

                # Step 4: Create DAG and analyze
                console.print("\n[cyan]Step 4:[/cyan] Analyzing session structure...")
                dag = ConversationDAG(loader, session_id)
                session = dag.to_session()

                console.print(f"  • Messages: {session.message_count}")
                console.print(f"  • Threads: {session.thread_count}")
                console.print(f"  • Corruption: {session.corruption_score:.2%}")

                # Step 5: Detect changes and log repairs
                repair_events = []

                if existing_session and len(existing_session) > 0:
                    console.print("\n[cyan]Step 5:[/cyan] Detecting changes...")

                    # Get existing messages from SurrealDB
                    msg_result = await db.query(
                        f"SELECT * FROM message WHERE session_id = '{session_id}'"
                    )
                    existing_messages = msg_result[0]["result"] if msg_result and msg_result[0].get("result") else []
                    existing_by_uuid = {m["message_uuid"]: m for m in existing_messages}

                    # Compare with current messages
                    for msg in messages:
                        existing = existing_by_uuid.get(msg.uuid)

                        if not existing:
                            # New message
                            import uuid
                            repair_events.append({
                                "event_id": str(uuid.uuid4()),
                                "session_id": session_id,
                                "message_id": msg.uuid,
                                "operator": args.operator or "cli",
                                "timestamp": datetime.now().isoformat(),
                                "reason": "New message detected in JSONL",
                                "old_parent_uuid": None,
                                "new_parent_uuid": msg.parent_uuid or "",
                                "validation_passed": True,
                            })
                        elif existing.get("parent_uuid") != msg.parent_uuid:
                            # Parent changed
                            import uuid
                            repair_events.append({
                                "event_id": str(uuid.uuid4()),
                                "session_id": session_id,
                                "message_id": msg.uuid,
                                "operator": args.operator or "cli",
                                "timestamp": datetime.now().isoformat(),
                                "reason": "Parent UUID changed in JSONL",
                                "old_parent_uuid": existing.get("parent_uuid"),
                                "new_parent_uuid": msg.parent_uuid or "",
                                "validation_passed": True,
                            })

                    console.print(f"  ✓ Found {len(repair_events)} changes")
                else:
                    console.print("\n[cyan]Step 5:[/cyan] Initial import (no changes to detect)")

                # Step 6: Write to SurrealDB (dry run check)
                if args.dry_run:
                    console.print("\n[yellow]DRY RUN - No changes written[/yellow]")
                    console.print(f"Would log {len(repair_events)} repair events")
                    console.print(f"Would sync {len(messages)} messages")
                    return 0

                console.print("\n[cyan]Step 6:[/cyan] Writing to SurrealDB...")

                # Create/update session record
                await db.query(f"""
                    CREATE session:{session_id} CONTENT {{
                        session_id: '{session_id}',
                        message_count: {session.message_count},
                        thread_count: {session.thread_count},
                        corruption_score: {session.corruption_score},
                        session_hash: '{session_hash}',
                        last_updated: time::now(),
                        created_at: time::now()
                    }} RETURN NONE
                """)

                # Log repair events (immutable append to repairs_events)
                for event in repair_events:
                    await db.create("repairs_events", event)

                # Update/create materialized view
                await db.query(f"""
                    CREATE sessions_materialized:{session_id} CONTENT {{
                        session_id: '{session_id}',
                        message_count: {session.message_count},
                        thread_count: {session.thread_count},
                        corruption_score: {session.corruption_score},
                        cached_at: time::now(),
                        repair_events_applied: {len(repair_events)}
                    }} RETURN NONE
                """)

                # Sync all messages (upsert)
                for msg in messages:
                    await db.query(f"""
                        CREATE message:{msg.uuid} CONTENT {{
                            session_id: '{session_id}',
                            message_uuid: '{msg.uuid}',
                            parent_uuid: {f"'{msg.parent_uuid}'" if msg.parent_uuid else 'NONE'},
                            message_type: '{msg.type.value}',
                            role: '{msg.type.value}',
                            content: {json.dumps(msg.content[:200])},
                            timestamp: '{msg.timestamp}',
                            is_orphaned: {str(msg.corruption_score > 0.5).lower()},
                            corruption_score: {msg.corruption_score}
                        }} RETURN NONE
                    """)

                console.print("  ✓ Synced session record")
                console.print(f"  ✓ Logged {len(repair_events)} repair events")
                console.print(f"  ✓ Synced {len(messages)} messages")

                # Step 7: Display report
                console.print("\n" + "=" * 60)
                console.print("[bold green]✓ Sync Complete[/bold green]\n")

                console.print("[bold]Session Status:[/bold]")
                console.print(f"  Messages: {session.message_count}")
                console.print(f"  Threads: {session.thread_count}")
                console.print(f"  Corruption: {session.corruption_score:.2%}")
                console.print(f"  Hash: {session_hash}")

                if repair_events:
                    console.print("\n[bold]Changes Logged:[/bold]")
                    console.print(f"  Repair events: {len(repair_events)}")

                console.print("\n[bold]Next Steps:[/bold]")
                console.print(f"  riff graph {session_id}  [dim]# View conversation graph[/dim]")
                console.print(f"  [dim]# SurrealDB query: SELECT * FROM session:{session_id}[/dim]")

                console.print("\n[dim]Note: JSONL is now reference-only.[/dim]")
                console.print("[dim]SurrealDB is the canonical source for this session.[/dim]")
                console.print("=" * 60)

                return 0

            # Run async function
            result = asyncio.run(sync_to_surrealdb())
            return result

        except ConnectionRefusedError:
            console.print(f"[red]Error: Cannot connect to SurrealDB at {db_url}[/red]")
            console.print("[yellow]Make sure SurrealDB is running:[/yellow]")
            console.print("  surreal start --bind 0.0.0.0:8000 --user root --pass root")
            return 1
        except Exception as e:
            console.print(f"[red]SurrealDB error: {e}[/red]")
            import traceback
            traceback.print_exc()
            return 1

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        traceback.print_exc()
        return 1


def _check_and_reindex_if_needed(qdrant_url: str) -> None:
    """
    Check if Claude projects directory has changed and auto-reindex if needed.
    Also validates that indexed sessions in Qdrant actually exist on disk.
    Uses pluggable manifest adapter - easily swappable for system-level manifest
    when that integration is ready.
    """
    import subprocess

    # Use manifest adapter (can be swapped out for system-level one)
    manifest = get_manifest_adapter()

    # Check for file-level changes
    needs_reindex = manifest.needs_reindex()
    reindex_reason = manifest.get_changes_summary() if needs_reindex else None

    # ALSO validate that Qdrant index points to files that actually exist
    if not needs_reindex:
        try:
            # Try to get indexed file paths from Qdrant
            searcher = QdrantSearcher(qdrant_url)
            indexed_paths = searcher.get_all_indexed_file_paths()

            # Validate that all indexed sessions exist
            if indexed_paths and not manifest.validate_index_integrity(indexed_paths):
                needs_reindex = True
                reindex_reason = manifest.get_changes_summary()
        except Exception as e:
            # If we can't check Qdrant, that's ok - just skip validation
            # (Qdrant might be starting up, etc.)
            pass

    if needs_reindex and reindex_reason:
        console.print(f"\n[cyan]📚 Detecting changes in Claude projects...[/cyan]")
        console.print(f"[dim]{reindex_reason} - reindexing[/dim]")

        # Run improved_indexer.py (canonical indexing source)
        try:
            indexer_script = Path(__file__).parent.parent.parent / "scripts" / "improved_indexer.py"
            # Use uv run to ensure dependencies are available
            result = subprocess.run(
                ["uv", "run", "python", str(indexer_script)],
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                console.print(f"[green]✓ Reindexing complete[/green]\n")
                manifest.save_manifest()
            else:
                console.print(f"[yellow]⚠️  Reindexing had issues: {result.stderr[:100]}[/yellow]\n")
        except Exception as e:
            console.print(f"[yellow]⚠️  Could not reindex: {e}[/yellow]\n")


def cmd_search(args) -> int:
    """Search Claude sessions with content preview"""
    try:
        searcher = QdrantSearcher(args.qdrant_url or "http://localhost:6333")

        # Check if Qdrant is available
        if not searcher.is_available():
            console.print(
                "[yellow]⚠️  Qdrant not available at {args.qdrant_url}[/yellow]\n"
                "[dim]Make sure Qdrant is running. See: ~/docs/federation/PORT_REGISTRY.md[/dim]"
            )
            return 1

        # Auto-check and reindex if projects directory has changed
        _check_and_reindex_if_needed(args.qdrant_url or "http://localhost:6333")

        # Perform search
        if args.uuid:
            result = searcher.search_by_uuid(args.query)
            if not result:
                console.print(f"[yellow]No session found with UUID: {args.query}[/yellow]")
                return 0
            results = [result]
        else:
            # Apply intent enhancement if requested
            if args.ai:
                enhancer = IntentEnhancer()
                query = enhancer.enhance_query(args.query)
                console.print(f"[dim]Enhanced query: {query}[/dim]")
            else:
                query = args.query

            # Build filter kwargs
            filter_kwargs = {}
            if args.days:
                filter_kwargs['days'] = args.days
            if args.since:
                filter_kwargs['since'] = args.since
            if args.until:
                filter_kwargs['until'] = args.until

            # Try semantic search first
            results = searcher.search(query, args.limit, args.min_score, **filter_kwargs)

            # Fallback to fuzzy matching if semantic search yields few results
            # (useful for exact phrase/word searches)
            if len(results) < 3:
                try:
                    fuzzy_results = searcher.search_fuzzy(query, args.limit, min_score=0.6)
                    if fuzzy_results:
                        # Merge results, preferring semantic matches
                        semantic_ids = {r.session_id for r in results}
                        for fuzzy_result in fuzzy_results:
                            if fuzzy_result.session_id not in semantic_ids:
                                results.append(fuzzy_result)
                        console.print(f"[dim]📝 Combined semantic + fuzzy matching (found {len(results)} total)[/dim]")
                except Exception as e:
                    console.print(f"[dim]Fuzzy matching unavailable: {e}[/dim]")

        # Display results with content preview
        preview = ContentPreview(console)
        preview.display_search_results(results, args.query, show_snippets=True)

        # Launch interactive TUI if requested
        if args.interactive and results:
            from .tui.prompt_toolkit_impl import PromptToolkitTUI

            # Convert SearchResult objects to dicts for TUI
            result_dicts = [
                {
                    'session_id': r.session_id,
                    'file_path': r.file_path,
                    'working_directory': r.working_directory,
                    'content_preview': r.content_preview,
                    'score': r.score
                }
                for r in results
            ]

            console.print("\n[cyan]🎮 Interactive Mode[/cyan]")
            console.print("[dim]Use j/k to navigate, Enter to open, o=preview, q to quit[/dim]\n")

            tui = PromptToolkitTUI(result_dicts, console)

            # Navigation loop - continues until user quits or opens session
            while True:
                nav_result = tui.navigate()

                # Handle navigation result
                if nav_result.action == "open" and nav_result.session_id:
                    selected = result_dicts[nav_result.selected_index]
                    console.print(f"\n[green]Opening session: {nav_result.session_id}[/green]")
                    tui.resume_session(
                        nav_result.session_id,
                        selected['file_path'],
                        selected.get('working_directory', str(Path.home()))
                    )
                    break  # Exit loop after opening
                elif nav_result.action == "preview" and nav_result.session_id:
                    # Show preview modal and continue navigation
                    selected = result_dicts[nav_result.selected_index]
                    console.print("\n")
                    tui.show_preview_modal(selected)
                    console.print("\n[dim]Returning to search results...[/dim]\n")
                    # Loop continues, user can navigate more
                elif nav_result.action == "filter":
                    console.print("\n[yellow]Time filtering not yet implemented in interactive mode[/yellow]")
                    console.print("[dim]Use --days, --since, --until flags instead[/dim]")
                    # Loop continues
                elif nav_result.action == "quit":
                    # User pressed 'q', exit loop
                    break

        return 0

    except ImportError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print(
            "[yellow]Install dependencies:[/yellow]\n"
            "  pip install qdrant-client sentence-transformers"
        )
        return 1
    except Exception as e:
        console.print(f"[red]Search error: {e}[/red]")
        return 1


def cmd_graph(args) -> int:
    """Visualize conversation as semantic DAG tree with pluggable repair backends"""
    import os

    try:
        # Set SurrealDB URL if provided via CLI
        if hasattr(args, 'surrealdb_url') and args.surrealdb_url:
            os.environ['SURREALDB_URL'] = args.surrealdb_url
            console.print(f"[dim]Using SurrealDB backend: {args.surrealdb_url}[/dim]")

        # Handle session ID or search query
        session_id = args.session_id

        # Check if it's a full path or just a UUID
        if "/" in session_id or "\\" in session_id:
            # It's a path
            session_path = Path(session_id)
            if not session_path.exists():
                console.print(f"[red]Error: File not found: {session_path}[/red]")
                return 1
            session_id = session_path.stem
            conversations_dir = session_path.parent
        else:
            # It's a UUID - look in default location
            conversations_dir = Path.home() / ".claude" / "projects"

            # Find the session file in any subdirectory
            found_path = None
            for jsonl_file in conversations_dir.rglob(f"{session_id}*.jsonl"):
                found_path = jsonl_file
                conversations_dir = jsonl_file.parent
                session_id = jsonl_file.stem
                break

            if not found_path:
                console.print(f"[yellow]Session {session_id} not found in {conversations_dir}[/yellow]")
                console.print("[dim]Tip: Use full path or ensure session UUID exists[/dim]")
                return 1

        # Load the session using JSONLLoader
        console.print(f"[dim]Loading session from {conversations_dir}...[/dim]")
        loader = JSONLLoader(conversations_dir)

        # Create DAG
        dag = ConversationDAG(loader, session_id)

        # Convert to session for analysis
        session = dag.to_session()

        # Get full JSONL path
        jsonl_path = None
        for jsonl_file in conversations_dir.glob("*.jsonl"):
            if session_id in jsonl_file.stem:
                jsonl_path = jsonl_file
                break

        # Show statistics
        console.print("\n[bold cyan]Session Statistics:[/bold cyan]")
        console.print(f"  Total messages: {session.message_count}")
        console.print(f"  Threads: {session.thread_count}")
        console.print(f"  Orphaned threads: {session.orphan_count}")
        console.print(f"  Corruption score: {session.corruption_score:.2%}")

        # Show thread details if present
        if session.main_thread:
            console.print(f"  Main thread messages: {session.main_thread.message_count}")
        if session.side_threads:
            console.print(f"  Side discussions: {len(session.side_threads)}")

        if args.interactive:
            # Launch interactive TUI navigator
            try:
                from .tui.graph_navigator import ConversationGraphNavigator

                navigator = ConversationGraphNavigator(
                    session=session,
                    dag=dag,
                    session_id=session_id,
                    jsonl_path=jsonl_path,
                    loader=loader
                )
                navigator.run()
            except ImportError:
                # Fallback to ASCII visualization
                console.print("\n[yellow]TUI navigator not available, showing ASCII tree:[/yellow]\n")
                visualizer = ConversationTreeVisualizer(session)
                tree_output = visualizer.render_ascii_tree()
                console.print(tree_output)
        else:
            # Just show ASCII visualization
            visualizer = ConversationTreeVisualizer(session)
            tree_output = visualizer.render_ascii_tree()
            console.print("\n[bold cyan]Conversation Tree:[/bold cyan]\n")
            console.print(tree_output)

        return 0

    except Exception as e:
        console.print(f"[red]Error visualizing conversation: {e}[/red]")
        import traceback
        traceback.print_exc()
        return 1


def cmd_browse(args) -> int:
    """Interactive vim-style conversation browser"""
    try:
        searcher = QdrantSearcher(args.qdrant_url or "http://localhost:6333")

        if not searcher.is_available():
            console.print(
                "[yellow]⚠️  Qdrant not available[/yellow]\n"
                "[dim]Make sure Qdrant is running.[/dim]"
            )
            return 1

        # Get all sessions (or search if query provided)
        if args.query:
            # TODO: Use search results in navigator
            searcher.search(args.query, args.limit)
            # Start vim-style navigator
            preview = ContentPreview(console)
            navigator = preview.create_interactive_navigator()
            navigator.navigate()
        else:
            # TODO: Implement "browse all" functionality
            console.print("[yellow]Browse mode coming soon![/yellow]")
            return 0

        return 0

    except Exception as e:
        console.print(f"[red]Browse error: {e}[/red]")
        return 1


def build_parser() -> argparse.ArgumentParser:
    """Build unified argument parser"""
    parser = argparse.ArgumentParser(
        prog="riff",
        description="Riff: search Claude conversations & repair JSONL sessions"
    )

    # Global options
    parser.add_argument("--qdrant-url", help="Qdrant server URL (default: http://localhost:6333)")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # ===== NEW SEARCH COMMANDS =====

    # Search command
    p_search = subparsers.add_parser(
        "search",
        help="Search Claude sessions with content preview"
    )
    p_search.add_argument("query", help="Search query or session UUID")
    p_search.add_argument("--limit", type=int, default=10, help="Number of results")
    p_search.add_argument("--min-score", type=float, default=0.15, help="Minimum similarity score (0.0-1.0, lower=more results)")
    p_search.add_argument("--uuid", action="store_true", help="Treat query as session UUID")
    p_search.add_argument("--ai", action="store_true", help="Use AI intent enhancement")
    p_search.add_argument("--days", type=int, help="Filter to sessions from past N days")
    p_search.add_argument("--since", help="Filter sessions since date (ISO 8601: YYYY-MM-DD)")
    p_search.add_argument("--until", help="Filter sessions until date (ISO 8601: YYYY-MM-DD)")
    p_search.add_argument("--interactive", action="store_true", default=True,
                        help="Launch interactive TUI navigator (default: True)")
    p_search.add_argument("--no-interactive", dest="interactive", action="store_false",
                        help="Show results only without TUI navigation")
    p_search.set_defaults(func=cmd_search)

    # Browse command
    p_browse = subparsers.add_parser(
        "browse",
        help="Interactive vim-style conversation browser"
    )
    p_browse.add_argument("query", nargs="?", default="", help="Optional search query to start with")
    p_browse.add_argument("--limit", type=int, default=20, help="Results to load")
    p_browse.set_defaults(func=cmd_browse)

    # ===== CLASSIC COMMANDS (PRESERVED) =====

    p_scan = subparsers.add_parser("scan", help="Scan for JSONL issues")
    p_scan.add_argument("target", nargs="?", default=".", help="Directory or file to scan")
    p_scan.add_argument("--glob", default="**/*.jsonl", help="Glob pattern")
    p_scan.add_argument("--show", action="store_true", help="Show issue details")
    p_scan.set_defaults(func=cmd_scan)

    p_fix = subparsers.add_parser("fix", help="Repair missing tool_result in JSONL")
    p_fix.add_argument("path", help="JSONL file to repair")
    p_fix.add_argument("--in-place", action="store_true", help="Write back to same file")
    p_fix.set_defaults(func=cmd_fix)

    p_tui = subparsers.add_parser("tui", help="Interactive TUI for JSONL browsing")
    p_tui.add_argument("target", nargs="?", default=".", help="Directory to browse")
    p_tui.add_argument("--glob", default="**/*.jsonl", help="File glob")
    p_tui.add_argument("--fzf", action="store_true", help="Use fzf for file picking")
    p_tui.set_defaults(func=cmd_tui)

    # Graph command - new semantic DAG visualization
    p_graph = subparsers.add_parser(
        "graph",
        help="Visualize conversation as semantic DAG tree"
    )
    p_graph.add_argument("session_id", help="Session UUID or path to JSONL file")
    p_graph.add_argument("--interactive", action="store_true", default=True,
                        help="Launch interactive TUI navigator (default: True)")
    p_graph.add_argument("--no-interactive", dest="interactive", action="store_false",
                        help="Show ASCII tree only without TUI")
    p_graph.add_argument("--surrealdb-url", help="SurrealDB HTTP API URL for repair backend (auto-detects SurrealDB if not specified)")
    p_graph.set_defaults(func=cmd_graph)

    # Classic graph command (for backwards compatibility)
    p_graph_classic = subparsers.add_parser(
        "graph-classic",
        help="Generate conversation graph (mermaid/dot format)"
    )
    p_graph_classic.add_argument("path", help="JSONL file path")
    p_graph_classic.add_argument("--format", choices=["dot", "mermaid"], default="mermaid")
    p_graph_classic.add_argument("--out", help="Output file path")
    p_graph_classic.set_defaults(func=cmd_graph_classic)

    # Sync to SurrealDB command - Phase 6B
    p_sync_surrealdb = subparsers.add_parser(
        "sync:surrealdb",
        help="Sync JSONL session to SurrealDB immutable event store"
    )
    p_sync_surrealdb.add_argument("session_id", help="Session UUID or path to JSONL file")
    p_sync_surrealdb.add_argument("--force", action="store_true",
                                 help="Force re-sync even if hash matches")
    p_sync_surrealdb.add_argument("--dry-run", action="store_true",
                                 help="Show what would be synced without writing")
    p_sync_surrealdb.add_argument("--operator", default="cli",
                                 help="Operator name for repair events (default: cli)")
    p_sync_surrealdb.add_argument("--surrealdb-url",
                                 help="SurrealDB WebSocket URL (default: ws://localhost:8000/rpc)")
    p_sync_surrealdb.set_defaults(func=cmd_sync_surrealdb)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point"""
    from argparse import Namespace

    parser = build_parser()
    args = parser.parse_args(argv)

    # If no command specified, launch TUI (browse mode with empty query)
    if not hasattr(args, 'func'):
        # Create mock args for browse command
        class BrowseArgs(Namespace):
            def __init__(self):
                super().__init__()
                self.query = ""
                self.limit = 20
                self.qdrant_url = None
                self.func = cmd_browse

        args = BrowseArgs()

    try:
        return args.func(args)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        return 130
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

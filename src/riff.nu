#!/usr/bin/env nu

# Riff CLI - Unified search across Claude exports and JSONL files
# Auto-detects format and provides intelligent defaults
# Usage: riff [search_term] [options]
# Version: 3.0.0 - Standalone Edition

def main [
    search_term?: string = "",           # Optional search term or intent description
    --path (-p): string = "",            # Base path to search (default: env RIFF_SEARCH_PATH or ~/.claude/projects)
    --format (-f): string = "auto",      # Format: jsonl, claude, auto
    --intent (-i),                       # Enable intent-driven search
    --recursive (-r): int = 3,           # Recursive enhancement depth (1-5)
    --no-fzf (-n),                       # Skip fzf and output directly
    --uuid-only (-u),                    # Output only UUIDs
    --json (-j),                         # Output as JSON
    --verbose (-v),                      # Verbose output with debug info
    --limit (-l): int = 1000,            # Limit results (default 1000)
    --progress                           # Show progress indicators during processing
] {

    # Lightweight debug toggle (avoids new CLI flags). Enable with: RIFF_DEBUG=true
    let debug = ($env | get -i RIFF_DEBUG | default "false" | into bool)

    # Determine search path with environment variable fallback
    let search_path = if ($path | str length) > 0 {
        $path
    } else {
        ($env | get -i RIFF_SEARCH_PATH | default "~/.claude/projects")
    }

    if $verbose {
        print $"🔍 Riff CLI v3.0 - Unified search in ($search_path)"
        print $"📝 Search term: '($search_term)'"
        print $"🧠 Intent mode: ($intent)"
        print $"🔄 Recursive depth: ($recursive)"
    }

    # Detect format if auto
    let search_format = if $format == "auto" {
        detect_format $search_path
    } else {
        $format
    }

    if $verbose {
        let claude_count = (glob ($search_path | path expand | path join "*.json") | length)
        let jsonl_count = (glob ($search_path | path expand | path join "**/*.jsonl") | length)
        let format_info = "Detected: " + $search_format + " (Claude: " + ($claude_count | into string) + ", JSONL: " + ($jsonl_count | into string) + ")"
        print $format_info
    }

    # Generate keywords based on intent if enabled
    let search_keywords = if $intent and ($search_term | str length) > 0 {
        if $verbose {
            print $"🧠 Starting intent-driven keyword generation for: '($search_term)'"
        }
        generate_search_keywords $search_term $recursive $verbose
    } else {
        if $verbose and ($search_term | str length) > 0 {
            print $"🔍 Using direct search term: '($search_term)'"
        }
        [$search_term]
    }

    if $verbose { print $"Keywords: ($search_keywords | str join ', ')" }

    # Execute search based on format
    if $verbose { print $"Format: ($search_format)" }

    let results = match $search_format {
        "claude" => {
            if $verbose { print "Searching Claude export..." }
            search_claude_export $search_path $search_keywords $limit $verbose $progress
        }
        "jsonl" => {
            if $verbose { print "Searching JSONL..." }
            search_jsonl_format $search_path $search_keywords $limit $verbose $progress
        }
        _ => {
            print "❌ Unsupported format or no files found"
            []
        }
    }

    if $verbose { print $"Results: ($results | length) before display" }

    # Process and display results
    display_results $results $json $uuid_only $no_fzf $verbose
}

# Import shared functions if available (optional for standalone)
try {
    use lib/riff-core.nu [collect-jsonl-files scan-file]
} catch {
    # Standalone mode without lib/riff-core.nu
}

# Detect file format in directory
def detect_format [path: string] {
    let claude_files = (glob ($path | path expand | path join "*.json") | length)
    let jsonl_files = (glob ($path | path expand | path join "**/*.jsonl") | length)

    # Prioritize JSONL if there are significantly more JSONL files
    if $jsonl_files > 0 and ($jsonl_files > $claude_files * 2) {
        "jsonl"
    } else if $claude_files > 0 {
        "claude"
    } else if $jsonl_files > 0 {
        "jsonl"
    } else {
        "unknown"
    }
}

# Generate search keywords using intent analysis
def generate_search_keywords [intent: string, depth: int, verbose: bool] {
    let keywords = [$intent]

    # Try Python intent enhancer if available (optional)
    let enhanced_result = try {
        # Look for intent_enhancer_simple.py in multiple locations
        let script_locations = [
            ($env | get -i RIFF_INTENT_SCRIPT | default ""),
            ($env.PWD | path join "intent_enhancer_simple.py"),
            ($env.PWD | path join "src/intent_enhancer_simple.py"),
            ($env.HOME | path join ".local/lib/riff/intent_enhancer_simple.py")
        ]

        let script_path = ($script_locations | where ($it | path exists) | first)

        if ($script_path | path exists) {
            python3 $script_path $intent $depth | from json
        } else {
            # Fallback to pattern-based expansion
            {enhanced_keywords: (expand_keywords_pattern $intent)}
        }
    } catch {
        if $verbose {
            print "Warning: Python intent enhancer not available, using pattern fallback"
        }
        {enhanced_keywords: (expand_keywords_pattern $intent)}
    }

    let expanded_keywords = $enhanced_result.enhanced_keywords

    if $verbose {
        print $"🧩 Enhanced keywords: ($expanded_keywords | str join ', ')"
        if ($enhanced_result | get routing | default null) != null {
            print $"🎯 Search strategy: ($enhanced_result.routing.strategy)"
        }
    }

    $keywords | append $expanded_keywords | uniq
}

# Pattern-based keyword expansion with partial matching support
def expand_keywords_pattern [intent: string] {
    let intent_lower = ($intent | str downcase)
    let keywords = []

    # Technical terms expansion with partial matching
    # Removed nabia-specific references for standalone version
    let keywords = if ($intent_lower | str contains "claude") {
        $keywords | append ["assistant", "conversation", "chat", "ai", "llm", "dialogue"]
    } else { $keywords }

    let keywords = if ($intent_lower | str contains "linear") {
        $keywords | append ["issue", "project", "task", "ticket", "workflow"]
    } else { $keywords }

    let keywords = if ($intent_lower | str contains "agent") {
        $keywords | append ["coordination", "protocol", "handoff", "distributed"]
    } else { $keywords }

    $keywords
}

# Search Claude export format (conversations.json, projects.json, users.json)
def search_claude_export [path: string, keywords: list, limit: int, verbose: bool, progress: bool] {
    let results = []

    # Search conversations
    let conv_file = ($path | path join "conversations.json")
    let results = if ($conv_file | path exists) {
        $results | append (search_conversations $conv_file $keywords $verbose)
    } else { $results }

    # Search projects
    let proj_file = ($path | path join "projects.json")
    let results = if ($proj_file | path exists) {
        $results | append (search_projects $proj_file $keywords $verbose)
    } else { $results }

    # Search users
    let user_file = ($path | path join "users.json")
    let results = if ($user_file | path exists) {
        $results | append (search_users $user_file $keywords $verbose)
    } else { $results }

    $results | flatten | take $limit
}

# Search conversations.json for keywords
def search_conversations [file_path: string, keywords: list, verbose: bool] {
    let debug = ($env | get -i RIFF_DEBUG | default "false" | into bool)
    if $verbose {
        print $"🗣️  Searching conversations: ($file_path)"
        let conv_count = (open $file_path | length)
        print $"📊 Found ($conv_count) conversations to search"
    }

    let conversations = (open $file_path)

    $conversations | each { |conv|
        let conv_text = ($conv.name + " " + ($conv.chat_messages | each { |msg| $msg.text } | str join " "))
        let matches_keywords = ($keywords | any { |keyword|
            ($conv_text | str downcase | str contains ($keyword | str downcase))
        })

        if $matches_keywords {
            if $debug { print $"✅ Conversation match: '($conv.name)' (UUID: ($conv.uuid))" }
            {
                type: "conversation",
                uuid: $conv.uuid,
                name: $conv.name,
                created_at: $conv.created_at,
                file: ($file_path | path basename),
                context: ($conv.name | str substring 0..150),
                match_text: ($conv_text | str substring 0..300)
            }
        } else {
            null
        }
    } | where $it != null | do {
        let results = $in
        if $verbose {
            print $"🗣️  Conversations search complete: ($results | length) matches found"
        }
        $results
    }
}

# Search projects.json for keywords
def search_projects [file_path: string, keywords: list, verbose: bool] {
    let debug = ($env | get -i RIFF_DEBUG | default "false" | into bool)
    if $verbose {
        print $"📁 Searching projects: ($file_path)"
        let proj_count = (open $file_path | length)
        print $"📊 Found ($proj_count) projects to search"
    }

    let projects = (open $file_path)

    $projects | each { |proj|
        let proj_text = ($proj.name + " " + $proj.description + " " +
                        ($proj.docs | each { |doc| $doc.content } | str join " "))
        let matches_keywords = ($keywords | any { |keyword|
            ($proj_text | str downcase | str contains ($keyword | str downcase))
        })

        if $matches_keywords {
            if $debug { print $"✅ Project match: '($proj.name)' (UUID: ($proj.uuid))" }
            {
                type: "project",
                uuid: $proj.uuid,
                name: $proj.name,
                description: $proj.description,
                created_at: $proj.created_at,
                file: ($file_path | path basename),
                context: ($proj.description | str substring 0..150),
                match_text: ($proj_text | str substring 0..300)
            }
        } else {
            null
        }
    } | where $it != null | do {
        let results = $in
        if $verbose {
            print $"📁 Projects search complete: ($results | length) matches found"
        }
        $results
    }
}

# Search users.json for keywords
def search_users [file_path: string, keywords: list, verbose: bool] {
    let debug = ($env | get -i RIFF_DEBUG | default "false" | into bool)
    if $verbose {
        print $"👤 Searching users: ($file_path)"
        let user_count = (open $file_path | length)
        print $"📊 Found ($user_count) users to search"
    }

    let users = (open $file_path)

    $users | each { |user|
        let user_text = ($user.full_name + " " + $user.email_address)
        let matches_keywords = ($keywords | any { |keyword|
            ($user_text | str downcase | str contains ($keyword | str downcase))
        })

        if $matches_keywords {
            if $debug { print $"✅ User match: '($user.full_name)' (UUID: ($user.uuid))" }
            {
                type: "user",
                uuid: $user.uuid,
                name: $user.full_name,
                email: $user.email_address,
                file: ($file_path | path basename),
                context: $user.full_name,
                match_text: $user_text
            }
        } else {
            null
        }
    } | where $it != null | do {
        let results = $in
        if $verbose {
            print $"👤 Users search complete: ($results | length) matches found"
        }
        $results
    }
}

# Search traditional JSONL format (fallback)
def search_jsonl_format [path: string, keywords: list, limit: int, verbose: bool, progress: bool] {
    if $verbose { print $"Searching JSONL in: ($path)" }

    let jsonl_files = (
        glob ($path | path expand | path join "**/*.jsonl")
        | where ($it | path type) == "file"
    )

    if $verbose { print $"Found ($jsonl_files | length) JSONL files" }

    if ($jsonl_files | length) == 0 {
        return []
    }

    # Process files with progress tracking
    let total_files = ($jsonl_files | length)
    let results = ($jsonl_files | enumerate | each { |file_info|
        let file_path = $file_info.item
        let file_index = $file_info.index

        if $progress and (not $verbose) {
            let spinner_frames = ["⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏"]
            let frame_index = ($file_index mod 10)
            let frame = ($spinner_frames | get $frame_index)
            let processed_count = ($file_index + 1)
            print -n $"\r⏳ Processing ($processed_count)/($total_files) files... ($frame)"
        }

        open $file_path
        | lines
        | enumerate
        | where ($it.item | str trim | str length) > 0
        | each { |line|
            try {
                let parsed = ($line.item | from json)
                let json_text = ($parsed | to json --raw | str downcase)
                let matches_keywords = ($keywords | any { |keyword|
                    ($json_text | str contains ($keyword | str downcase))
                })

                if $matches_keywords {
                    # Extract useful fields
                    let uuid = (extract_uuid_from_parsed $parsed)
                    let cwd = ($parsed | get -i cwd | default "")
                    let summary = ($parsed | get -i summary | default "")
                    let message_content = ($parsed | get -i message | default {} | get -i content | default "")

                    # Create meaningful snippet from message content
                    let snippet = if ($message_content | describe) == "string" and ($message_content | str length) > 0 {
                        # Clean up multi-line content and take first meaningful line
                        let clean_content = ($message_content | str replace -a '\n' ' ' | str replace -a '\r' ' ' | str trim)
                        ($clean_content | str substring 0..150)
                    } else if ($message_content | describe) == "list" {
                        ($message_content | each { |item|
                            if ($item | describe) == "string" { $item }
                            else if ($item | get -i content) { $item.content }
                            else { "" }
                        } | str join " " | str substring 0..150)
                    } else {
                        # Try to extract from other fields
                        let tool_result = ($parsed | get -i toolUseResult | default {} | get -i file | default {} | get -i content | default "")
                        if ($tool_result | str length) > 0 {
                            let clean_result = ($tool_result | str replace -a '\n' ' ' | str replace -a '\r' ' ' | str trim)
                            ($clean_result | str substring 0..150)
                        } else {
                            "No readable content"
                        }
                    }

                    {
                        type: "jsonl",
                        uuid: $uuid,
                        cwd: $cwd,
                        summary: $summary,
                        snippet: $snippet,
                        file: ($file_path | path basename),
                        line: ($line.index + 1)
                    }
                } else {
                    null
                }
            } catch {
                null
            }
        }
        | where $it != null
    })

    let final_results = ($results | flatten | take $limit)

    if $progress and (not $verbose) {
        print -n "\r                                                                                \r"
    }

    $final_results
}

# Extract UUID from parsed JSON object
def extract_uuid_from_parsed [parsed: any] {
    let uuid_fields = ["uuid", "sessionId", "leafUuid", "id"]

    $uuid_fields | each { |field|
        try {
            let value = ($parsed | get $field)
            if ($value | describe) == "string" and ($value | str length) == 36 {
                $value
            } else {
                null
            }
        } catch {
            null
        }
    } | where $it != null | first
}

# Display results based on output options
def display_results [results: any, json_output: bool, uuid_only: bool, no_fzf: bool, verbose: bool] {
    if ($results | length) == 0 {
        print "No results found matching your criteria."
        return
    }

    if $verbose {
        print $"Matches: ($results | length)"
        let breakdown = ($results | group-by type | transpose type count | each {|row| ($row.type) + ": " + ($row.count | length | into string)} | str join ', ')
        print $"Breakdown: ($breakdown)"
    }

    if $json_output {
        if $verbose { print "Output: JSON" }
        $results | to json
    } else if $uuid_only {
        if $verbose { print $"Output: UUIDs only (unique: ($results | get uuid | uniq | length))" }
        $results | get uuid | uniq
    } else if $no_fzf {
        if $verbose { print "Output: direct list (no fzf)" }
        $results | each { |result|
            # Format: UUID | CWD | Summary | Snippet
            let uuid = ($result | get -i uuid | default "unknown")
            let cwd = ($result | get -i cwd | default "")
            let summary = ($result | get -i summary | default "")
            let snippet = ($result | get -i snippet | default "")

            # Create clean display
            let cwd_display = if ($cwd | str length) > 0 {
                ($cwd | path basename)
            } else {
                "unknown"
            }

            let summary_display = if ($summary | str length) > 0 {
                $summary
            } else {
                "No summary"
            }

            let snippet_display = if ($snippet | str length) > 0 {
                ($snippet | str substring 0..80)
            } else {
                "No content"
            }

            $"UUID: ($uuid) | DIR: ($cwd_display) | SUMMARY: ($summary_display) | SNIPPET: ($snippet_display)"
        }
    } else {
        if $verbose { print "Preparing fzf selection" }
        # Prepare data for fzf
        let fzf_input = (
            $results | each { |result|
                # Format: UUID | CWD | Summary | Snippet
                let uuid = ($result | get -i uuid | default "unknown")
                let cwd = ($result | get -i cwd | default "")
                let summary = ($result | get -i summary | default "")
                let snippet = ($result | get -i snippet | default "")

                # Create clean display
                let cwd_display = if ($cwd | str length) > 0 {
                    ($cwd | path basename)
                } else {
                    "unknown"
                }

                let summary_display = if ($summary | str length) > 0 {
                    $summary
                } else {
                    "No summary"
                }

                let snippet_display = if ($snippet | str length) > 0 {
                    ($snippet | str substring 0..80)
                } else {
                    "No content"
                }

                $"UUID: ($uuid) | DIR: ($cwd_display) | SUMMARY: ($summary_display) | SNIPPET: ($snippet_display)"
            }
            | str join (char nl)
        )

        # Use fzf for interactive selection
        try {
            if $verbose { print $"Launching fzf with ($fzf_input | lines | length) options" }
            let selected = (
                $fzf_input
                | fzf --multi --preview 'echo {}' --preview-window 'up:3:wrap' --prompt 'Select result(s): ' --header 'Use arrow keys to navigate, Enter to select, Tab for multiple'
            )

            if ($selected | str length) > 0 {
                if $verbose { print $"Selected ($selected | lines | length) items" }
                $selected | lines
            } else {
                if $verbose { print "No selection made" }
                []
            }
        } catch {
            if $verbose { print "fzf not available or cancelled" }
            []
        }
    }
}

# Help function
def "main help" [] {
    print "
🎶 Riff CLI v3.0 - Unified Claude Export & JSONL Search (Standalone Edition)

USAGE:
    riff [SEARCH_TERM] [OPTIONS]

ARGUMENTS:
    SEARCH_TERM    Search term or intent description (optional)

OPTIONS:
    -p, --path PATH        Search path (default: env RIFF_SEARCH_PATH or ~/.claude/projects)
    -f, --format FORMAT    Format: jsonl, claude, auto (default: auto)
    -i, --intent          Enable intent-driven search
    -r, --recursive NUM   Recursive enhancement depth (1-5, default: 3)
    -n, --no-fzf         Skip fzf and output directly
    -u, --uuid-only      Output only UUIDs
    -j, --json           Output as JSON
    -v, --verbose        Verbose output with debug info
    -l, --limit NUM      Limit results (default: 1000)
    --progress           Show progress indicators during processing
    -h, --help           Show this help message

ENVIRONMENT VARIABLES:
    RIFF_SEARCH_PATH      Default search path for Claude exports
    RIFF_INTENT_SCRIPT    Path to intent_enhancer_simple.py (optional)
    RIFF_DEBUG            Enable debug output (true/false)

EXAMPLES:
    riff 'search term'                         # Basic search
    riff 'search term' --intent                # Intent-driven search
    riff 'find discussions' -i -r 5            # Deep recursive search
    riff --path ~/archive --format claude      # Specific path and format
    riff 'claude' --json --uuid-only           # JSON output, UUIDs only
    riff --progress                            # Show progress during search

FEATURES:
    • Auto-detects Claude export vs JSONL format
    • Intent-driven keyword expansion (optional Python script)
    • Recursive search enhancement
    • Claude Desktop export support (conversations, projects, users)
    • Traditional JSONL fallback support
    • Interactive fzf interface
    • Multiple output formats
    • Progress indicators

CLAUDE EXPORT SUPPORT:
    • Searches conversation messages, names, and metadata
    • Searches project docs, names, and descriptions
    • Searches user information
    • Automatic format detection

The tool automatically detects Claude export vs JSONL format and adapts search accordingly.
"
}

#!/usr/bin/env nu

# Riff CLI - Enhanced Claude Export Search with Intent-driven Recursive Search
# Usage: riff-claude [search_term] [options]
# Version: 2.0.0 - Claude Export Support

def main [
    search_term?: string = "",           # Optional search term or intent description
    --path (-p): string = "~/.claude/projects",  # Base path to search (default: Claude projects)
    --format (-f): string = "auto",     # Format: jsonl, claude, auto
    --intent (-i),                      # Enable intent-driven search
    --recursive (-r): int = 3,          # Recursive enhancement depth (1-5)
    --no-fzf (-n),                      # Skip fzf and output directly
    --uuid-only (-u),                   # Output only UUIDs
    --json (-j),                        # Output as JSON
    --verbose (-v),                     # Verbose output with debug info
    --limit (-l): int = 1000           # Limit results (default 1000)
] {
    
    if $verbose {
        print $"🔍 Riff CLI Claude - Enhanced search in ($path)"
        print $"📝 Search term: '($search_term)'"
        print $"🧠 Intent mode: ($intent)"
        print $"🔄 Recursive depth: ($recursive)"
    }
    
    # Detect format if auto
    let search_format = if $format == "auto" {
        detect_format $path
    } else {
        $format
    }
    
    if $verbose {
        print $"📊 Detected format: ($search_format)"
    }
    
    # Generate keywords based on intent if enabled
    let search_keywords = if $intent and ($search_term | str length) > 0 {
        generate_search_keywords $search_term $recursive $verbose
    } else {
        [$search_term]
    }
    
    if $verbose and $intent {
        print $"🎯 Generated keywords: ($search_keywords | str join ', ')"
    }
    
    # Execute search based on format
    let results = match $search_format {
        "claude" => { search_claude_export $path $search_keywords $limit $verbose }
        "jsonl" => { search_jsonl_format $path $search_keywords $limit $verbose }
        _ => { 
            print "❌ Unsupported format or no files found"
            []
        }
    }
    
    # Process and display results
    display_results $results $json $uuid_only $no_fzf $verbose
}

# Detect file format in directory
def detect_format [path: string] {
    let claude_files = (glob ($path | path expand | path join "*.json") | length)
    let jsonl_files = (glob ($path | path expand | path join "**/*.jsonl") | length)
    
    if $claude_files > 0 and ($claude_files >= $jsonl_files) {
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

    # Use Python intent enhancer for advanced keyword generation
    let enhanced_result = try {
        python3 ~/nabia/tools/riff-cli/src/intent_enhancer_simple.py $intent $depth | from json
    } catch {
        if $verbose {
            print "Warning: Python intent enhancer failed, using pattern fallback"
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
    let keywords = if ($intent_lower | str contains "nabia") or ($intent_lower | str contains "nabi") {
        $keywords | append ["nabia", "federation", "memchain", "orchestration", "agent", "coordination"]
    } else { $keywords }

    let keywords = if ($intent_lower | str contains "claude") {
        $keywords | append ["assistant", "conversation", "chat", "ai", "llm", "dialogue"]
    } else { $keywords }

    let keywords = if ($intent_lower | str contains "federation") {
        $keywords | append ["agent", "coordination", "protocol", "handoff", "distributed"]
    } else { $keywords }

    let keywords = if ($intent_lower | str contains "linear") {
        $keywords | append ["issue", "project", "task", "ticket", "workflow"]
    } else { $keywords }

    $keywords
}

# Search Claude export format (conversations.json, projects.json, users.json)
def search_claude_export [path: string, keywords: list, limit: int, verbose: bool] {
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
    if $verbose {
        print $"🗣️  Searching conversations: ($file_path)"
    }
    
    let conversations = (open $file_path)
    
    $conversations | each { |conv|
        let conv_text = ($conv.name + " " + ($conv.chat_messages | each { |msg| $msg.text } | str join " "))
        let matches_keywords = ($keywords | any { |keyword| 
            ($conv_text | str downcase | str contains ($keyword | str downcase))
        })
        
        if $matches_keywords {
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
    } | where $it != null
}

# Search projects.json for keywords
def search_projects [file_path: string, keywords: list, verbose: bool] {
    if $verbose {
        print $"📁 Searching projects: ($file_path)"
    }
    
    let projects = (open $file_path)
    
    $projects | each { |proj|
        let proj_text = ($proj.name + " " + $proj.description + " " + 
                        ($proj.docs | each { |doc| $doc.content } | str join " "))
        let matches_keywords = ($keywords | any { |keyword| 
            ($proj_text | str downcase | str contains ($keyword | str downcase))
        })
        
        if $matches_keywords {
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
    } | where $it != null
}

# Search users.json for keywords
def search_users [file_path: string, keywords: list, verbose: bool] {
    if $verbose {
        print $"👤 Searching users: ($file_path)"
    }
    
    let users = (open $file_path)
    
    $users | each { |user|
        let user_text = ($user.full_name + " " + $user.email_address)
        let matches_keywords = ($keywords | any { |keyword| 
            ($user_text | str downcase | str contains ($keyword | str downcase))
        })
        
        if $matches_keywords {
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
    } | where $it != null
}

# Search traditional JSONL format (fallback)
def search_jsonl_format [path: string, keywords: list, limit: int, verbose: bool] {
    if $verbose {
        print $"📄 Searching JSONL files in: ($path)"
    }
    
    let jsonl_files = (
        glob ($path | path expand | path join "**/*.jsonl")
        | where ($it | path type) == "file"
    )
    
    if ($jsonl_files | length) == 0 {
        return []
    }
    
    $jsonl_files | each { |file_path|
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
                    {
                        type: "jsonl",
                        uuid: (extract_uuid_from_parsed $parsed),
                        file: ($file_path | path basename),
                        line: ($line.index + 1),
                        context: ($json_text | str substring 0..150),
                        match_text: ($json_text | str substring 0..300)
                    }
                } else { 
                    null 
                }
            } catch {
                null
            }
        }
        | where $it != null
    } | flatten | take $limit
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
        print $"🎯 Found ($results | length) matches"
    }
    
    if $json_output {
        $results | to json
    } else if $uuid_only {
        $results | get uuid | uniq
    } else if $no_fzf {
        $results | each { |result|
            # Safe field access: try 'name' first, fallback to 'context'
            let name_field = ($result | get -i name)
            let display_name = if ($name_field != null and ($name_field | str length) > 0) {
                $name_field
            } else {
                ($result | get -i context | default "")
            }
            $"($result.type) | ($result.uuid) | ($display_name) | ($result.file)"
        }
    } else {
        # Prepare data for fzf
        let fzf_input = (
            $results | each { |result|
                # Safe field access: try 'name' first, fallback to 'context'
                let name_field = ($result | get -i name)
                let display_name = if ($name_field != null and ($name_field | str length) > 0) {
                    $name_field
                } else {
                    ($result | get -i context | default "")
                }
                $"($result.type) | ($result.uuid) | ($display_name) | ($result.file)"
            }
            | str join (char nl)
        )
        
        # Use fzf for interactive selection
        try {
            let selected = (
                $fzf_input 
                | fzf --multi --preview 'echo {}' --preview-window 'up:3:wrap' --prompt 'Select result(s): ' --header 'Use arrow keys to navigate, Enter to select, Tab for multiple'
            )
            
            if ($selected | str length) > 0 {
                $selected | lines
            }
        } catch {
            []
        }
    }
}

# Help function
def "main help" [] {
    print "
🎶 Riff CLI Claude - Enhanced Claude Export Search

USAGE:
    riff-claude [SEARCH_TERM] [OPTIONS]

ARGUMENTS:
    SEARCH_TERM    Search term or intent description

OPTIONS:
    -p, --path PATH        Search path (default: current directory)
    -f, --format FORMAT    Format: jsonl, claude, auto (default: auto)
    -i, --intent          Enable intent-driven search  
    -r, --recursive NUM   Recursive enhancement depth (1-5, default: 3)
    -n, --no-fzf         Skip fzf and output directly  
    -u, --uuid-only      Output only UUIDs
    -j, --json           Output as JSON
    -v, --verbose        Verbose output with debug info
    -l, --limit NUM      Limit results (default: 1000)
    -h, --help           Show this help message

EXAMPLES:
    riff-claude 'nabia federation'                    # Basic search
    riff-claude 'nabia federation' --intent           # Intent-driven search
    riff-claude 'find linear discussions' -i -r 5     # Deep recursive search
    riff-claude --path ~/archive --format claude      # Specific path and format
    riff-claude 'claude' --json --uuid-only          # JSON output, UUIDs only

FEATURES:
    • Claude export format support (conversations.json, projects.json, users.json)
    • Intent-driven keyword expansion
    • Recursive search enhancement
    • Traditional JSONL fallback support
    • Interactive fzf interface
    • Multiple output formats

CLAUDE EXPORT SUPPORT:
    • Searches conversation messages, names, and metadata
    • Searches project docs, names, and descriptions  
    • Searches user information
    • Automatic format detection

The tool automatically detects Claude export vs JSONL format and adapts search accordingly.
"
}
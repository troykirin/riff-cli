#!/usr/bin/env nu

# Riff CLI - Fuzzy search for UUIDs in Claude conversation logs
# Usage: riff [search_term] [options]
# Version: 1.2.0

def main [
    search_term?: string = "",           # Optional search term to filter content
    --path (-p): string = "~/.claude/projects",  # Base path to search
    --no-fzf (-n),                      # Skip fzf and output directly
    --uuid-only (-u),                   # Output only UUIDs
    --json (-j),                        # Output as JSON
    --verbose (-v),                     # Verbose output with debug info
    --limit (-l): int = 1000            # Limit results (default 1000)
] {
    
    # If no search term and not UUID-only mode, warn the user
    if ($search_term | str length) == 0 and (not $uuid_only) and (not $no_fzf) {
        print "
⚠️  No search term provided. This will scan ALL files and may take a while.
    Tip: Provide a search term to filter results, or use --uuid-only for faster output.
    Example: riff linear
    Processing..."
    }
    
    if $verbose {
        print $"🔍 Riff CLI - Searching for UUIDs in ($path)"
        print $"📝 Search term: '($search_term)'"
    }
    
    # Find all JSONL files recursively
    let jsonl_files = (
        glob ($path | path expand | path join "**/*.jsonl")
        | where ($it | path type) == "file"
    )
    
    let total_files = ($jsonl_files | length)
    
    if $verbose {
        print $"📁 Found ($total_files) JSONL files"
    }

    # Show processing message
    if not $verbose {
        print -n $"⏳ Processing ($total_files) files... "
    }
    
    # Process each JSONL file and extract UUIDs with context
    let results = (
        $jsonl_files 
        | enumerate
        | each { |file_info|
            let file_path = $file_info.item
            let file_index = $file_info.index
            
            if $verbose {
                print -n "."  # Progress indicator
            } else if (($file_index mod 10) == 0) {
                # Show spinner for every 10 files
                let spinner = ["⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏"]
                let frame_index = ((($file_index / 10) mod 10) | into int)
                let frame = ($spinner | get $frame_index)
                print -n $"\r⏳ Processing ($total_files) files... $frame \(($file_index + 1)/($total_files)\)"
            }
            
            open $file_path
            | lines
            | enumerate
            | where ($it.item | str trim | str length) > 0
            | each { |line|
                try {
                    let parsed = ($line.item | from json)
                    let line_num = ($line.index + 1)
                    
                    # Extract UUIDs from all string fields that look like UUIDs
                    let uuids = (
                        $parsed 
                        | transpose key value 
                        | where ($it.value | describe) == "string" 
                            and ($it.value | str length) == 36 
                            and ($it.value | str contains "-")
                        | each { |field|
                            let parts = ($field.value | split row "-")
                            if ($parts | length) == 5 {
                                {
                                    file: ($file_path | path basename),
                                    full_path: $file_path,
                                    line: $line_num,
                                    uuid: $field.value,
                                    field: $field.key,
                                    context: ($parsed | to json --raw | str substring 0..150)
                                }
                            } else { null }
                        }
                        | where $it != null
                    )
                    
                    # Filter based on search term if provided
                    if ($search_term | str length) > 0 {
                        let json_text = ($parsed | to json --raw | str downcase)
                        if ($json_text | str contains ($search_term | str downcase)) {
                            $uuids
                        } else {
                            []
                        }
                    } else {
                        $uuids
                    }
                } catch {
                    []
                }
            }
            | flatten
        }
        | flatten
        | take $limit  # Apply limit to results
    )
    
    # Clear the progress line
    if not $verbose {
        print -n "\r                                                                                "
        print -n "\r"
    } else {
        print ""  # New line after progress dots
    }
    
    if ($results | length) == 0 {
        print "No UUIDs found matching your criteria."
        return
    }
    
    if $verbose {
        print $"🎯 Found ($results | length) UUID matches (limited to $limit)"
    }

    # Format output based on options
    if $json {
        $results | to json
    } else if $uuid_only {
        $results | get uuid | uniq
    } else if $no_fzf {
        $results | each { |result|
            $"($result.uuid) | ($result.file):($result.line) | ($result.field) | ($result.context)"
        }
    } else {
        # Prepare data for fzf
        let fzf_input = (
            $results | each { |result|
                $"($result.uuid) | ($result.file):($result.line) | ($result.field) | ($result.context)"
            }
            | str join (char nl)
        )
        
        # Use fzf for interactive selection
        try {
            let selected = (
                $fzf_input 
                | fzf --multi --preview 'echo {}' --preview-window 'up:3:wrap' --prompt 'Select UUID(s): ' --header 'Use arrow keys to navigate, Enter to select, Tab for multiple'
            )
            
            if ($selected | str length) > 0 {
                # Extract just the UUIDs from selected lines
                $selected 
                | lines 
                | each { |line| 
                    ($line | split row ' | ' | get 0)
                }
            }
        } catch {
            # If fzf was cancelled or failed
            []
        }
    }
}

# Help function
def "main help" [] {
    print "
🎶 Riff CLI - Fuzzy UUID Search Tool

USAGE:
    riff [SEARCH_TERM] [OPTIONS]

ARGUMENTS:
    SEARCH_TERM    Optional text to search within JSON content

OPTIONS:
    -p, --path PATH     Search path (default: ~/.claude/projects)
    -n, --no-fzf       Skip fzf and output directly  
    -u, --uuid-only    Output only UUIDs
    -j, --json         Output as JSON
    -v, --verbose      Verbose output with debug info
    -l, --limit NUM    Limit results (default: 1000)
    -h, --help         Show this help message

EXAMPLES:
    riff                           # Interactive search (may be slow!)
    riff linear                    # Search for UUIDs in entries containing 'linear'
    riff -u                        # List all UUIDs without fzf
    riff linear --json            # JSON output for 'linear' matches
    riff --path ~/other/dir       # Search in different directory
    riff --limit 100              # Limit to first 100 results
    
FEATURES:
    • Recursively searches all .jsonl files
    • Extracts UUIDs from any JSON field (sessionId, leafUuid, uuid, etc.)
    • Fuzzy search interface with fzf
    • Context preview showing surrounding content
    • Multiple output formats (interactive, JSON, UUID-only)
    • Result limiting for performance

TIPS:
    • For best performance, always provide a search term
    • Use --uuid-only for quick UUID extraction
    • The tool processes files sequentially, so large directories may be slow

The tool is designed for Claude Code conversation logs but works with any JSONL format.
"
}
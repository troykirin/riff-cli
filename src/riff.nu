#!/usr/bin/env nu

use lib/riff-core.nu [collect-jsonl-files scan-file]

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
    let jsonl_files = collect-jsonl-files $path
    
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
                print -n $"\r⏳ Processing ($total_files) files... ($frame) \(($file_index + 1)/($total_files)\)"
            }

            scan-file $file_path --search-term $search_term --context-length 150
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
        print $"🎯 Found ($results | length) UUID matches with limit ($limit)"
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
        # Build entry metadata for interactive selection
        let entries = (
            $results
            | each { |result|
                let preview_value = ($result | get preview?)
                let raw_snippet = (
                    if (($preview_value | describe) == "nothing") {
                        $result.context
                    } else if (($preview_value | str length) == 0) {
                        $result.context
                    } else {
                        $preview_value
                    }
                )
                let snippet = (
                    if ($raw_snippet | str length) == 0 {
                        "(no preview available)"
                    } else if ($raw_snippet | str length) > 1200 {
                        [($raw_snippet | str substring 0..1200), "…"] | str join
                    } else {
                        $raw_snippet
                    }
                )
                let dir_path = ($result.full_path | path dirname)
                let display_label = $"($result.uuid)  ($result.file):($result.line)  [$result.field]"
                let preview_block = $"UUID : ($result.uuid)\nFile : ($result.full_path)\nLine : ($result.line)\nField: ($result.field)\nDir  : ($dir_path)\n\n($snippet)"
                {
                    display: $display_label,
                    preview: $preview_block,
                    uuid: $result.uuid,
                    full_path: $result.full_path,
                    dir: $dir_path,
                    cd: $"cd ($dir_path)",
                    cc: $"cc -r ($result.uuid)",
                    claude: $"claude -r ($result.uuid)"
                }
            }
        )

        let temp_file = (mktemp)
        $entries | to json | save -f $temp_file

        let fzf_input = (
            $entries
            | enumerate
            | each { |it|
                let idx = $it.index
                let display_line = $it.item.display
                $"($idx)\t[($idx)] ($display_line)"
            }
            | str join (char nl)
        )

        let preview_cmd = $"nu -c 'open "($temp_file)" | get {{1}} | get preview'"

        try {
            let selected = (
                $fzf_input
                | fzf --ansi --multi --delimiter "\t" --with-nth=2 --preview $preview_cmd --preview-window 'up,60%,wrap' --prompt 'Select entry: ' --header 'Enter: copy commands | Tab: multi-select'
            )

            let output = (
                if ($selected | str length) > 0 {
                    let selection_indices = (
                        $selected
                        | lines
                        | where ($it | str length) > 0
                        | each { |line|
                            ($line | split row '\t' | get 0 | into int)
                        }
                    )

                    let data = (open $temp_file)
                    let chosen = (
                        $selection_indices
                        | each { |idx| $data | get $idx }
                    )

                    $chosen | enumerate | each { |item|
                        let entry = $item.item
                        if $item.index > 0 {
                            print ""
                        }
                        print $"UUID : ($entry.uuid)"
                        print $"Path : ($entry.full_path)"
                        print $"Dir  : ($entry.dir)"
                        print "Commands:" 
                        print $"  ($entry.cd)"
                        print $"  ($entry.cc)"
                        print $"  ($entry.claude)"
                    }

                    $chosen | get uuid
                } else {
                    []
                }
            )

            rm $temp_file
            $output
        } catch {
            rm $temp_file
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
#!/usr/bin/env nu

# Riff CLI Enhanced - With progress indicators
# Version: 2.0.0

def main [
    search_term?: string = "",           # Optional search term to filter content
    --path (-p): string = "~/.claude/projects",  # Base path to search
    --no-fzf (-n),                      # Skip fzf and output directly
    --uuid-only (-u),                   # Output only UUIDs
    --json (-j),                        # Output as JSON
    --verbose (-v),                     # Verbose output with debug info
    --limit (-l): int = 1000,           # Limit results (default 1000)
    --no-progress                       # Disable progress indicator
] {
    
    # If no search term and not UUID-only mode, warn the user
    if ($search_term | str length) == 0 and (not $uuid_only) and (not $no_fzf) {
        print "
⚠️  No search term provided. This will scan ALL files and may take a while.
    Tip: Provide a search term to filter results, or use --uuid-only for faster output.
    Example: riff linear"
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
    
    # Spinner frames for animation
    let spinner_frames = ["⠋" "⠙" "⠹" "⠸" "⠼" "⠴" "⠦" "⠧" "⠇" "⠏"]
    let mut current_frame = 0
    let mut processed_files = 0
    
    # Process each JSONL file and extract UUIDs with context
    let results = (
        $jsonl_files 
        | enumerate
        | each { |file_info|
            let file_path = $file_info.item
            let file_index = $file_info.index
            
            # Update progress display
            if not $no_progress {
                $processed_files = $file_index + 1
                $current_frame = ($file_index mod 10)
                
                # Calculate percentage
                let percentage = (($processed_files * 100) / $total_files)
                
                # Create progress bar
                let bar_width = 30
                let filled = (($percentage * $bar_width) / 100)
                let empty = ($bar_width - $filled)
                let progress_bar = (
                    ("█" | str repeat $filled) + 
                    ("░" | str repeat $empty)
                )
                
                # Print progress on same line
                print -n $"\r($spinner_frames | get $current_frame) Processing: [$progress_bar] ($percentage)% \(($processed_files)/($total_files)\) files"
            }
            
            # Process the file
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
    if not $no_progress {
        print -n $"\r(ansi erase_line_from_cursor_to_end)"
    }
    
    if ($results | length) == 0 {
        print "❌ No UUIDs found matching your criteria."
        return
    }
    
    print $"✅ Found ($results | length) UUID matches (limited to $limit)"
    
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
🎶 Riff CLI Enhanced - Fuzzy UUID Search with Progress Indicators

USAGE:
    riff-enhanced [SEARCH_TERM] [OPTIONS]

ARGUMENTS:
    SEARCH_TERM    Optional text to search within JSON content

OPTIONS:
    -p, --path PATH      Search path (default: ~/.claude/projects)
    -n, --no-fzf        Skip fzf and output directly  
    -u, --uuid-only     Output only UUIDs
    -j, --json          Output as JSON
    -v, --verbose       Verbose output with debug info
    -l, --limit NUM     Limit results (default: 1000)
    --no-progress       Disable progress indicator
    -h, --help          Show this help message

FEATURES:
    • Animated spinner during processing
    • Progress bar showing percentage complete
    • File counter (X/Y files processed)
    • Clean output after processing
    • All original riff features

EXAMPLES:
    riff-enhanced linear                # Search with progress bar
    riff-enhanced --no-progress        # Disable progress indicator
    riff-enhanced linear --limit 100   # Limit with progress tracking
"
}
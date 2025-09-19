#!/usr/bin/env nu

use lib/riff-core.nu [collect-jsonl-files scan-files]

# Simplified Riff CLI for testing
def main [
    search_term?: string = "",
    --path (-p): string = "~/.claude/projects"
] {
    let jsonl_files = collect-jsonl-files $path
    
    let results = (
        scan-files $jsonl_files --search-term $search_term --context-length 0
    )
    
    $results | get uuid | uniq
}
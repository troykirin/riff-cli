#!/usr/bin/env nu

# Simplified Riff CLI for testing
def main [search_term?: string = ""] {
    let jsonl_files = (glob "~/.claude/projects/**/*.jsonl" | where ($it | path type) == "file")
    
    let results = (
        $jsonl_files 
        | each { |file_path|
            open $file_path
            | lines
            | enumerate
            | where ($it.item | str trim | str length) > 0
            | each { |line|
                try {
                    let parsed = ($line.item | from json)
                    let line_num = ($line.index + 1)
                    
                    # Extract UUIDs from all string fields
                    let uuids = (
                        $parsed 
                        | transpose key value 
                        | where ($it.value | describe) == "string" and ($it.value | str length) == 36 and ($it.value | str contains "-")
                        | each { |field|
                            {
                                file: ($file_path | path basename),
                                line: $line_num,
                                uuid: $field.value,
                                field: $field.key,
                                context: (if ($search_term | str length) > 0 { ($parsed | to json --raw | str substring 0..100) } else { "" })
                            }
                        }
                    )
                    
                    # Filter by search term if provided
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
    )
    
    $results | get uuid | uniq
}
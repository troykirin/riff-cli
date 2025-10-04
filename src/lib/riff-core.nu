# Shared utilities for Riff CLI variants

export def collect-jsonl-files [
    path: string
] {
    glob ($path | path expand | path join "**/*.jsonl")
    | where ($it | path type) == "file"
}

export def scan-file [
    file_path: string,
    --search-term: string = "",
    --context-length: int = 150
] {
    let use_search = ($search_term | str length) > 0
    let normalized_search = ($search_term | str downcase)

    open $file_path
    | lines
    | enumerate
    | where ($it.item | str trim | str length) > 0
    | each { |line|
        try {
            let parsed = ($line.item | from json)
            let line_num = ($line.index + 1)

            let pretty_json = ($parsed | to json)
            let preview_lines = (
                $pretty_json
                | lines
                | take 40
            )
            let preview_text = ($preview_lines | str join (char nl))

            let context_snippet = (
                if $context_length > 0 {
                    $pretty_json | str replace (char nl) " " | str substring 0..$context_length
                } else {
                    ""
                }
            )

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
                            context: $context_snippet,
                            preview: $preview_text
                        }
                    } else { null }
                }
                | where $it != null
            )

            if $use_search {
                let json_text = ($parsed | to json --raw | str downcase)
                if ($json_text | str contains $normalized_search) {
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

export def scan-files [
    files: list<string>,
    --search-term: string = "",
    --limit: int = 0,
    --context-length: int = 150
] {
    let gathered = (
        $files
        | each { |file_path|
            scan-file $file_path --search-term $search_term --context-length $context_length
        }
        | flatten
    )

    if $limit > 0 {
        $gathered | take $limit
    } else {
        $gathered
    }
}

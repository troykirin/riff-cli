#!/usr/bin/env nu

# Index Claude Export - Pre-process conversations.json into searchable index
# Usage: index-claude-export [export_path] [output_path]
# Version: 1.0.0

def main [
    export_path: string = "/Volumes/Extreme Pro/nabia-federation-backup/claude-exports/data-2025-10-21-18-50-30-batch-0000",
    output_path: string = "~/.local/share/nabi/claude-export-index.jsonl",
    --verbose (-v)
] {
    print $"📚 Indexing Claude export: ($export_path)"

    let conv_file = ($export_path | path join "conversations.json")

    if not ($conv_file | path exists) {
        print $"❌ Error: conversations.json not found at ($conv_file)"
        return
    }

    print "🔍 Loading conversations (this may take a moment for large files)..."
    let conversations = (open $conv_file)

    print $"📊 Found ($conversations | length) conversations"

    # Ensure output directory exists
    let output_dir = ($output_path | path expand | path dirname)
    mkdir $output_dir

    print $"💾 Creating index at ($output_path | path expand)"

    # Process each conversation into a searchable record
    let index_records = (
        $conversations
        | enumerate
        | each { |conv_with_idx|
            let conv = $conv_with_idx.item
            let idx = $conv_with_idx.index

            if $verbose and (($idx + 1) mod 100 == 0) {
                print $"   Processed ($idx + 1) / ($conversations | length) conversations..."
            }

            # Extract all message text into searchable content
            let all_text = (
                $conv.chat_messages
                | each { |msg| $msg.text }
                | str join " "
            )

            # Create searchable index record
            {
                uuid: $conv.uuid,
                name: $conv.name,
                summary: ($conv.summary | default ""),
                created_at: $conv.created_at,
                updated_at: $conv.updated_at,
                message_count: ($conv.chat_messages | length),
                searchable_text: $all_text,
                # Store first 500 chars for preview
                preview: ($all_text | str substring 0..500)
            }
        }
    )

    # Write to JSONL format (one JSON object per line)
    $index_records
    | each { |record| $record | to json --raw }
    | str join (char nl)
    | save --force ($output_path | path expand)

    let file_size = (ls ($output_path | path expand) | get size | first)

    print $"✅ Index created successfully!"
    print $"   - Location: ($output_path | path expand)"
    print $"   - Conversations: ($conversations | length)"
    print $"   - File size: ($file_size)"
    print $""
    print $"💡 You can now search this index with riff-cli:"
    print $"   riff splunk 'your query' --sources claude"
}

# Development Guide

Guide for developing and contributing to Riff CLI.

## Development Setup

### Prerequisites

1. **Nushell**: Install the latest version
   ```bash
   # macOS
   brew install nushell
   
   # Linux
   curl -s https://raw.githubusercontent.com/nushell/nushell/main/scripts/install.sh | bash
   ```

2. **fzf**: For fuzzy finding functionality
   ```bash
   # macOS
   brew install fzf
   
   # Linux
   sudo apt install fzf  # or equivalent for your distro
   ```

3. **Git**: For version control and contribution workflow

### Local Development

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd riff-cli
   ```

2. Make scripts executable for testing:
   ```bash
   chmod +x src/*.nu
   ```

3. Test locally without installation:
   ```bash
   ./src/riff.nu test-data.jsonl
   ./src/riff-enhanced.nu test-data.jsonl
   ./src/riff-simple.nu test-data.jsonl
   ```

## Project Architecture

### Core Components

- **`src/riff.nu`**: Main implementation with full feature set
- **`src/riff-enhanced.nu`**: Enhanced version with progress indicators
- **`src/riff-simple.nu`**: Minimal version for testing and debugging

### Key Features

1. **UUID Extraction**: Regex-based UUID detection from JSON objects
2. **Fuzzy Search Integration**: `fzf` integration for interactive selection
3. **Multiple Output Formats**: Interactive, JSON, UUID-only modes
4. **Content Filtering**: Search within JSON content
5. **Performance Optimization**: Streaming and limiting for large files

### Code Structure

```nushell
# Typical flow in riff.nu
def main [file: string, ...args] {
    # 1. Parse command line arguments
    let options = parse_args($args)
    
    # 2. Read and validate JSONL file  
    let data = read_jsonl($file)
    
    # 3. Extract UUIDs from JSON objects
    let uuids = extract_uuids($data)
    
    # 4. Apply content filtering if requested
    let filtered = filter_content($uuids, $options.search)
    
    # 5. Format output based on requested mode
    match $options.format {
        "interactive" => fuzzy_select($filtered),
        "json" => format_json($filtered),
        "uuid" => format_uuid_only($filtered)
    }
}
```

## Testing

### Test Data

Create test JSONL files in `tests/sample-data/`:

```bash
# Create basic test file
cat > tests/sample-data/basic.jsonl << 'EOF'
{"id": "123e4567-e89b-12d3-a456-426614174000", "content": "test data one"}
{"id": "987fcdeb-51a2-43d1-b789-123456789abc", "content": "test data two"}
{"id": "550e8400-e29b-41d4-a716-446655440000", "content": "test data three"}
EOF

# Create large test file for performance testing
for i in {1..1000}; do
    echo "{\"id\": \"$(uuidgen | tr '[:upper:]' '[:lower:]')\", \"index\": $i, \"content\": \"test item $i\"}"
done > tests/sample-data/large.jsonl
```

### Manual Testing

```bash
# Test all variants
./src/riff.nu tests/sample-data/basic.jsonl
./src/riff-enhanced.nu tests/sample-data/basic.jsonl  
./src/riff-simple.nu tests/sample-data/basic.jsonl

# Test different output formats
./src/riff.nu tests/sample-data/basic.jsonl --uuid-only
./src/riff.nu tests/sample-data/basic.jsonl --json

# Test search functionality
./src/riff.nu tests/sample-data/basic.jsonl --search "one"

# Test performance with large file
./src/riff-enhanced.nu tests/sample-data/large.jsonl --limit 10
```

### Installation Testing

```bash
# Test installation process
./install/install.sh

# Verify aliases work
riff tests/sample-data/basic.jsonl
riff-uuid tests/sample-data/basic.jsonl

# Test uninstallation
./install/uninstall.sh
```

## Contributing

### Code Style

Follow Nushell best practices:

1. **Use descriptive function names**: `extract_uuids` instead of `get_ids`
2. **Type annotations**: Specify parameter types where helpful
3. **Error handling**: Use `try` blocks and meaningful error messages
4. **Comments**: Document complex logic and regex patterns
5. **Modularity**: Break complex functions into smaller, focused functions

### Development Workflow

1. **Branch naming**: Use descriptive names like `feature/enhanced-search` or `fix/uuid-regex`

2. **Commit messages**: Follow conventional commits:
   ```
   feat: add content-based search functionality
   fix: handle malformed JSON lines gracefully
   docs: update usage examples in README
   test: add performance test with large dataset
   ```

3. **Testing checklist**:
   - [ ] All variants work with test data
   - [ ] Installation/uninstallation scripts work
   - [ ] Shell aliases function correctly
   - [ ] Error handling works for edge cases
   - [ ] Performance acceptable with large files

### Common Development Tasks

#### Adding a New Feature

1. Implement in `src/riff.nu` first
2. Test thoroughly with various inputs
3. Add to enhanced version if appropriate
4. Update documentation
5. Add test cases

#### Debugging Issues

1. Use `riff-simple.nu` to isolate the problem
2. Add debug prints with `print` statements
3. Test with minimal JSONL data
4. Check regex patterns with online tools

#### Performance Optimization

1. Profile with large datasets
2. Use `time ./src/riff.nu large-file.jsonl` 
3. Consider streaming vs. batch processing
4. Test memory usage with monitoring tools

### File Structure Guidelines

```
src/
├── riff.nu           # Main implementation - most features
├── riff-enhanced.nu  # Enhanced UI/UX features  
└── riff-simple.nu    # Minimal, debugging-friendly

install/
├── install.sh        # Cross-platform installation
├── uninstall.sh      # Clean removal
└── zsh-aliases.sh    # Shell integration

docs/
├── usage.md          # User documentation
├── development.md    # This file
└── conversation-log.md # Development history

tests/
└── sample-data/      # Test JSONL files
```

## Known Issues and Limitations

### Current Limitations

1. **UUID Format**: Only supports standard UUID format (8-4-4-4-12)
2. **Shell Integration**: Currently only supports Zsh aliases  
3. **Large Files**: Memory usage grows with file size
4. **Error Recovery**: Limited recovery from malformed JSON

### Future Enhancements

1. **Multi-format UUID support**: UUIDv1, v4, v5, custom formats
2. **Shell Integration**: Bash, Fish shell support
3. **Streaming Parser**: True streaming for massive files
4. **Configuration**: User config file for defaults
5. **Output Formats**: CSV, XML, custom formats

## Architecture Decisions

### Why Nushell?

- **Structured data**: Native JSON/JSONL support
- **Pipeline-friendly**: Natural data flow paradigm
- **Cross-platform**: Consistent behavior across systems
- **Modern tooling**: Better error handling and type safety

### Why fzf Integration?

- **User Experience**: Fast, intuitive fuzzy searching
- **Ubiquitous**: Available on all major platforms
- **Performant**: Handles large lists efficiently
- **Customizable**: Can be styled and configured

### Three Variant Strategy

- **riff.nu**: Full-featured, production-ready
- **riff-enhanced.nu**: Experimental features, enhanced UX
- **riff-simple.nu**: Minimal, debuggable, educational

This allows for:
- Stable main implementation
- Feature experimentation without breaking main
- Simple debugging and learning tool
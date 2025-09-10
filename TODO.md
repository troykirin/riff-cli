
  ⎿  Riff CLI Project Organization Plan

     Overview

     Create a dedicated riff-cli directory to consolidate the entire Riff CLI implementation with proper project structure,
     documentation, and version control.

     Project Structure

     ~/nabia/riff-cli/
     ├── README.md                    # Main project documentation
     ├── DEVELOPMENT.md              # Development notes and conversation context
     ├── src/                        # Source code
     │   ├── riff.nu                 # Main CLI implementation (copy from ~/.local/bin/riff)
     │   ├── riff-enhanced.nu        # Enhanced version with progress (from ~/.local/bin/riff-enhanced)
     │   └── riff-simple.nu          # Simple test version (from ~/.local/bin/riff-simple)
     ├── install/                    # Installation and setup scripts
     │   ├── install.sh              # Main installation script
     │   ├── zsh-aliases.sh          # Shell integration aliases
     │   └── uninstall.sh            # Clean removal script
     ├── docs/                       # Documentation
     │   ├── usage.md                # Usage examples and guides
     │   ├── development.md          # Development setup
     │   └── conversation-log.md     # This entire conversation preserved
     ├── tests/                      # Test files and examples
     │   └── sample-data/            # Sample JSONL files for testing
     └── .git/                       # Git repository for version control

     Implementation Steps

     1. Project Setup

     - Create ~/nabia/riff-cli/ directory
     - Initialize git repository
     - Set up directory structure

     2. Source Code Migration

     - Copy existing working scripts from ~/.local/bin/:
       - riff → src/riff.nu
       - riff-enhanced → src/riff-enhanced.nu
       - riff-simple → src/riff-simple.nu

     3. Installation System

     - Create install/install.sh that:
       - Copies scripts to ~/.local/bin/
       - Makes them executable
       - Sets up zsh aliases
       - Verifies nushell and fzf dependencies
     - Create install/zsh-aliases.sh with existing aliases plus:
       - alias riff='~/.local/bin/riff'
       - alias riff-uuid='riff --uuid-only'
       - alias riff-json='riff --json'
       - alias riff-help='riff help'

     4. Documentation

     - README.md: Project overview, installation, basic usage
     - docs/usage.md: Comprehensive usage examples
     - docs/development.md: Development setup and contributing
     - docs/conversation-log.md: This entire conversation preserved as context

     5. Git History

     Create atomic commits:
     - Initial project structure
     - Core riff implementation
     - Enhanced version with progress indicators
     - Installation and shell integration
     - Documentation and examples

     6. Testing Setup

     - Create sample JSONL files for testing
     - Document test procedures
     - Verify installation process

     Key Features to Document

     - Nushell-based UUID extraction from JSONL files
     - Fuzzy search with fzf integration
     - Multiple output formats (interactive, JSON, UUID-only)
     - Progress indicators for large file processing
     - Content-based filtering with search terms
     - Performance optimizations (limiting, streaming)

     Benefits

     - Standalone Project: Complete self-contained implementation
     - Version Control: Proper git history and change tracking
     - Easy Installation: Simple setup process for new users
     - Documentation: Comprehensive usage and development guides
     - Context Preservation: Full conversation history for future reference
     - Reproducible: Anyone can clone and install the complete toolchain


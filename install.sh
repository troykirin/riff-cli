#!/usr/bin/env bash

# Riff CLI Installation Script
# Standalone version for open-source release

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Installation paths
INSTALL_DIR="${HOME}/.local/bin"
LIB_DIR="${HOME}/.local/lib/riff"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Main installation function
main() {
    print_info "Starting Riff CLI installation..."

    # Check for Nushell
    if ! command_exists nu; then
        print_error "Nushell (nu) is not installed. Please install it first:"
        print_error "  Visit: https://www.nushell.sh/"
        exit 1
    fi

    print_success "Nushell found: $(nu --version)"

    # Check for fzf (optional but recommended)
    if ! command_exists fzf; then
        print_warning "fzf is not installed. Interactive mode will not work."
        print_warning "Install fzf for the best experience: https://github.com/junegunn/fzf"
    else
        print_success "fzf found: $(fzf --version)"
    fi

    # Check for Python 3 (optional for intent enhancement)
    if ! command_exists python3; then
        print_warning "Python 3 is not installed. Intent-driven search will use pattern fallback."
        print_warning "Install Python 3 for enhanced search capabilities."
    else
        print_success "Python 3 found: $(python3 --version)"
    fi

    # Create installation directories
    print_info "Creating installation directories..."
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$LIB_DIR"

    # Copy main script
    print_info "Installing riff CLI to $INSTALL_DIR/riff..."
    cp "$SCRIPT_DIR/src/riff.nu" "$INSTALL_DIR/riff"
    chmod +x "$INSTALL_DIR/riff"

    # Copy library files
    if [ -d "$SCRIPT_DIR/src/lib" ]; then
        print_info "Installing library files to $LIB_DIR..."
        cp -r "$SCRIPT_DIR/src/lib/"* "$LIB_DIR/"
    fi

    # Copy Python intent enhancer (optional)
    if [ -f "$SCRIPT_DIR/src/intent_enhancer_simple.py" ]; then
        print_info "Installing intent enhancer to $LIB_DIR..."
        cp "$SCRIPT_DIR/src/intent_enhancer_simple.py" "$LIB_DIR/"
        chmod +x "$LIB_DIR/intent_enhancer_simple.py"
    fi

    # Check if ~/.local/bin is in PATH
    if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
        print_warning "$INSTALL_DIR is not in your PATH"
        print_warning "Add this to your shell configuration (~/.bashrc, ~/.zshrc, etc.):"
        echo ""
        echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        echo ""
    else
        print_success "$INSTALL_DIR is already in your PATH"
    fi

    # Create environment variable configuration suggestion
    print_info "Optional: Set environment variables for customization"
    echo ""
    echo "  export RIFF_SEARCH_PATH=\"\$HOME/.claude/projects\"  # Default search path"
    echo "  export RIFF_INTENT_SCRIPT=\"\$HOME/.local/lib/riff/intent_enhancer_simple.py\"  # Intent enhancer"
    echo "  export RIFF_DEBUG=false  # Debug output"
    echo ""

    # Verify installation
    print_info "Verifying installation..."
    if [ -x "$INSTALL_DIR/riff" ]; then
        print_success "Riff CLI installed successfully!"
        print_success "Run 'riff --help' to get started"
    else
        print_error "Installation failed. Please check the output above for errors."
        exit 1
    fi

    # Print next steps
    echo ""
    print_info "Next steps:"
    echo "  1. Ensure ~/.local/bin is in your PATH (see warning above if needed)"
    echo "  2. Restart your shell or run: source ~/.bashrc (or ~/.zshrc)"
    echo "  3. Test the installation: riff --help"
    echo "  4. Try a search: riff 'your search term'"
    echo ""
    print_info "For more information, see: docs/INSTALLATION.md"
}

# Run main installation
main "$@"

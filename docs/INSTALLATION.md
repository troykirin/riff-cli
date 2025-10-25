# Installation Guide

Complete installation instructions for Riff CLI.

## Prerequisites

### Required

- **Nushell** (v0.80.0+)
  ```bash
  # macOS
  brew install nushell

  # Linux
  # Download from https://github.com/nushell/nushell/releases

  # Or use cargo
  cargo install nu
  ```

### Optional (but recommended)

- **fzf** - For interactive fuzzy search
  ```bash
  # macOS
  brew install fzf

  # Linux
  sudo apt install fzf  # Debian/Ubuntu
  sudo dnf install fzf  # Fedora
  ```

- **Python 3** - For intent-driven search enhancement
  ```bash
  # Most systems have Python 3 installed
  python3 --version
  ```

## Installation Methods

### Method 1: Make Install (Recommended)

```bash
git clone https://github.com/yourusername/riff-cli.git
cd riff-cli
make install
```

This will:
- Check for required dependencies
- Install `riff` to `~/.local/bin/`
- Copy library files to `~/.local/lib/riff/`
- Make the script executable

### Method 2: Manual Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/riff-cli.git
cd riff-cli

# Run installation script
./install.sh
```

### Method 3: Manual Setup

```bash
# Copy main script
cp src/riff.nu ~/.local/bin/riff
chmod +x ~/.local/bin/riff

# Copy libraries (optional but recommended)
mkdir -p ~/.local/lib/riff
cp -r src/lib/* ~/.local/lib/riff/
cp src/intent_enhancer_simple.py ~/.local/lib/riff/
```

## Post-Installation

### Add to PATH

Ensure `~/.local/bin` is in your PATH:

**Bash/Zsh:**
```bash
# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"

# Then reload
source ~/.bashrc  # or source ~/.zshrc
```

**Fish:**
```fish
# Add to ~/.config/fish/config.fish
set -gx PATH $HOME/.local/bin $PATH
```

**Nushell:**
```nushell
# Add to ~/.config/nushell/env.nu
$env.PATH = ($env.PATH | prepend ($env.HOME | path join ".local/bin"))
```

### Environment Variables (Optional)

Create a configuration file or add to your shell RC:

```bash
# Default search path
export RIFF_SEARCH_PATH="$HOME/.claude/projects"

# Intent enhancer script location
export RIFF_INTENT_SCRIPT="$HOME/.local/lib/riff/intent_enhancer_simple.py"

# Enable debug output
export RIFF_DEBUG=false
```

## Verification

Test your installation:

```bash
# Check if riff is available
which riff

# Run help
riff --help

# Test dependencies
make test
```

Expected output:
```
✓ Nushell is installed
✓ fzf is installed
✓ Python 3 is installed
All required dependencies are installed
```

## Troubleshooting

### Command not found

If you get `command not found: riff`:
1. Check if `~/.local/bin` is in your PATH: `echo $PATH`
2. Restart your shell or run `source ~/.bashrc` (or equivalent)
3. Verify the file exists: `ls -la ~/.local/bin/riff`

### Permission denied

If you get permission errors:
```bash
chmod +x ~/.local/bin/riff
```

### fzf not working

Riff will still work without fzf, but you'll need to use `--no-fzf`:
```bash
riff "search" --no-fzf
```

Or install fzf:
```bash
# macOS
brew install fzf

# Linux
sudo apt install fzf
```

### Python intent enhancer not working

The intent enhancer is optional. Riff will fall back to pattern-based expansion if:
- Python 3 is not installed
- `intent_enhancer_simple.py` is not found
- The script fails to execute

To debug:
```bash
# Test Python
python3 --version

# Test intent enhancer manually
python3 ~/.local/lib/riff/intent_enhancer_simple.py "test query" 3
```

## Uninstallation

```bash
# Using make
make uninstall

# Or manually
rm ~/.local/bin/riff
rm -rf ~/.local/lib/riff
```

## Upgrading

```bash
cd riff-cli
git pull
make install
```

## Platform-Specific Notes

### macOS

- Homebrew provides the easiest installation for Nushell and fzf
- No special configuration needed

### Linux

- Most distributions have Nushell and fzf in their repositories
- Ensure `~/.local/bin` is created and in PATH

### Windows (WSL)

- Works well under WSL2
- Follow Linux installation instructions
- Ensure WSL has access to your Claude export directory

## Next Steps

- Read [USAGE.md](USAGE.md) for usage examples
- Try the examples in the `examples/` directory
- Customize with environment variables
- Enable intent-driven search with Python

## Support

For issues or questions:
- Check the [troubleshooting section](#troubleshooting)
- Open an issue on GitHub
- See the main [README](../README.md) for project overview

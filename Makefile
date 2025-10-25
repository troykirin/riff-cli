.PHONY: help install uninstall test clean

# Default target
help:
	@echo "Riff CLI - Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  make install     - Install riff CLI to ~/.local/bin"
	@echo "  make uninstall   - Remove riff CLI from ~/.local/bin"
	@echo "  make test        - Run basic tests"
	@echo "  make clean       - Clean temporary files"
	@echo "  make help        - Show this help message"

# Install riff CLI
install:
	@echo "Installing riff CLI..."
	@bash install.sh

# Uninstall riff CLI
uninstall:
	@echo "Uninstalling riff CLI..."
	@rm -f ~/.local/bin/riff
	@rm -rf ~/.local/lib/riff
	@echo "Riff CLI uninstalled successfully"

# Run basic tests
test:
	@echo "Running basic tests..."
	@if command -v nu >/dev/null 2>&1; then \
		echo "✓ Nushell is installed"; \
	else \
		echo "✗ Nushell is not installed"; \
		exit 1; \
	fi
	@if command -v fzf >/dev/null 2>&1; then \
		echo "✓ fzf is installed"; \
	else \
		echo "⚠ fzf is not installed (optional)"; \
	fi
	@if command -v python3 >/dev/null 2>&1; then \
		echo "✓ Python 3 is installed"; \
	else \
		echo "⚠ Python 3 is not installed (optional)"; \
	fi
	@echo "All required dependencies are installed"

# Clean temporary files
clean:
	@echo "Cleaning temporary files..."
	@find . -name "*.bak" -delete
	@find . -name "*~" -delete
	@echo "Clean complete"

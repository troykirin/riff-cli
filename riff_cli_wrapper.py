#!/usr/bin/env python
"""
PyInstaller-compatible wrapper for Riff CLI.
This script properly imports and calls the main function with package context.
"""

import sys

# Import and call the main function from riff.cli
from riff.cli import main

if __name__ == "__main__":
    sys.exit(main())

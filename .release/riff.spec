# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for Riff CLI single-binary release"""

block_cipher = None

# Core dependencies to include
hiddenimports = [
    'riff',
    'riff.config',
    'riff.backup',
    'riff.classic',
    'riff.classic.commands.scan',
    'riff.classic.commands.fix',
    'riff.classic.commands.tui',
    'riff.classic.commands.graph',
    'riff.search',
    'riff.enhance',
    'riff.graph',
    'riff.visualization',
    'toml',
    'rich',
    'click',
]

# Optional dependencies that should be excluded by default
excludedimports = [
    'sentence-transformers',  # Heavy, optional for search
    'qdrant-client',          # Optional for search
    'surrealdb',              # Optional for db sync
]

a = Analysis(
    ['.release/riff_cli_wrapper.py'],
    pathex=['.', 'src'],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    excludes=excludedimports,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='riff',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

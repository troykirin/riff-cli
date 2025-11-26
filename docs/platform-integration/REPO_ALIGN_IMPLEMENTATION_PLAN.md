# nabi repo align - Implementation Plan

**Linear Issue**: [NOS-671](https://linear.app/nabia/issue/NOS-671/implement-nabi-repo-align-for-automated-repository-compliance)

**Created**: 2025-10-26

---

## Executive Summary

Automated repository compliance validation to prevent federation drift. Frees the `align` agent to focus on semantic resonance rather than mechanical validation.

## Command Structure

### Top-Level Command Addition

```rust
// Add to Commands enum in main.rs (line 26)
#[derive(Subcommand)]
enum Commands {
    // ... existing commands ...

    /// Repository compliance validation
    Repo {
        #[command(subcommand)]
        command: RepoCommands,
    },
}

#[derive(Subcommand)]
enum RepoCommands {
    /// Check repository compliance (exit code based validation)
    Check {
        /// Path to repository (defaults to current directory)
        #[arg(short, long)]
        path: Option<String>,

        /// Output format (text, json, markdown)
        #[arg(short, long, default_value = "text")]
        format: OutputFormat,

        /// Strict mode (exit non-zero on warnings)
        #[arg(short, long)]
        strict: bool,

        /// Specific standards to validate
        #[arg(long, value_delimiter = ',')]
        standards: Option<Vec<Standard>>,
    },

    /// Generate detailed compliance report
    Report {
        /// Path to repository
        #[arg(short, long)]
        path: Option<String>,

        /// Output file (stdout if not specified)
        #[arg(short, long)]
        output: Option<String>,

        /// Group violations by category
        #[arg(short, long)]
        grouped: bool,
    },

    /// Fix compliance issues (interactive mode)
    Fix {
        /// Path to repository
        #[arg(short, long)]
        path: Option<String>,

        /// Dry run (show changes without applying)
        #[arg(long)]
        dry_run: bool,

        /// Non-interactive mode (auto-apply safe fixes)
        #[arg(short = 'y', long)]
        yes: bool,

        /// Create backup before fixing
        #[arg(short, long, default_value = "true")]
        backup: bool,
    },

    /// Validate specific compliance standards
    Validate {
        /// Path to repository
        #[arg(short, long)]
        path: Option<String>,

        /// Specific standard to validate
        #[arg(value_enum)]
        standard: Standard,
    },
}

#[derive(Clone, ValueEnum)]
enum Standard {
    /// XDG Base Directory Specification compliance
    Xdg,
    /// Virtual environment location standards
    Venv,
    /// Hardcoded path detection
    Paths,
    /// Federation integration patterns
    Federation,
    /// Documentation structure compliance
    Docs,
    /// All standards (default)
    All,
}

#[derive(Clone, ValueEnum)]
enum OutputFormat {
    Text,
    Json,
    Markdown,
}
```

### Handler Function

```rust
// Add to match statement in main() (line 535)
Commands::Repo { command } => handle_repo(command),

fn handle_repo(command: RepoCommands) -> Result<()> {
    match command {
        RepoCommands::Check { path, format, strict, standards } => {
            let repo_path = path.unwrap_or_else(|| ".".to_string());
            println!("{}", format!("🔍 Checking repository compliance: {}", repo_path).cyan().bold());

            // Implementation delegated to repo module
            repo::check(&repo_path, format, strict, standards)
        }
        RepoCommands::Report { path, output, grouped } => {
            let repo_path = path.unwrap_or_else(|| ".".to_string());
            println!("{}", format!("📊 Generating compliance report: {}", repo_path).cyan().bold());

            repo::report(&repo_path, output, grouped)
        }
        RepoCommands::Fix { path, dry_run, yes, backup } => {
            let repo_path = path.unwrap_or_else(|| ".".to_string());
            if dry_run {
                println!("{}", format!("🔍 Dry run: {}", repo_path).yellow().bold());
            } else {
                println!("{}", format!("🔧 Fixing compliance issues: {}", repo_path).green().bold());
            }

            repo::fix(&repo_path, dry_run, yes, backup)
        }
        RepoCommands::Validate { path, standard } => {
            let repo_path = path.unwrap_or_else(|| ".".to_string());
            println!("{}", format!("✓ Validating {:?} compliance: {}", standard, repo_path).cyan().bold());

            repo::validate(&repo_path, standard)
        }
    }
}
```

---

## Validation Rules

### From Link Mapper (~/Sync/docs/.ops/validation/validation_rules.yaml)

**XDG Compliance Rules:**

| Rule ID | Pattern | Required | Description |
|---------|---------|----------|-------------|
| `xdg_config` | `\$XDG_CONFIG_HOME` | Yes | Configuration paths must use XDG variable |
| `xdg_cache` | `\$XDG_CACHE_HOME` | Yes | Cache paths must use XDG variable |
| `xdg_state` | `\$XDG_STATE_HOME` | Yes | State paths must use XDG variable |
| `xdg_data` | `\$XDG_DATA_HOME` | Yes | Data paths must use XDG variable |

**Path Validation Rules:**

| Rule ID | Pattern | Must NOT Match | Description |
|---------|---------|----------------|-------------|
| `no_hardcoded_users` | `/Users/tryk\|/home/[a-zA-Z0-9_-]+` | Yes | No hardcoded user paths |
| `home_expansion` | `\$HOME\|~/` | Yes (required) | Use $HOME or ~/ for home directory |

**Federation Standards:**

| Rule ID | Pattern | Required | Description |
|---------|---------|----------|-------------|
| `tool_namespace` | `/nabi/{tool}/` | Yes | Tool-specific paths must be namespaced |
| `federation_integration` | `federation\|Federation` | Yes (in docs) | Must mention federation |
| `nabi_cli_documented` | `nabi (exec\|list\|resolve)` | Yes | nabi-cli integration documented |

**Exceptions:**
- Lines with `<!-- EXAMPLE` comment
- Code blocks (markdown fenced code)
- Inline code snippets (backticks)

### From Manifest System

**File Integrity Checks:**
- SHA256 validation for tracked files
- Drift detection (files modified without manifest update)
- Missing file detection

**Documentation Structure:**
- Links to `~/docs/` (federated, synced)
- Project-local docs in `./docs/`
- Proper MASTER_INDEX.md references

---

## Implementation Architecture

### Module Structure

```
~/nabia/core/nabi-cli/src/
├── main.rs                      # Command definitions (updated)
├── repo/
│   ├── mod.rs                   # Public API exports
│   ├── check.rs                 # Check command implementation
│   ├── report.rs                # Report generation
│   ├── fix.rs                   # Auto-remediation
│   ├── validate.rs              # Standard-specific validation
│   └── validators/
│       ├── mod.rs               # Validator trait
│       ├── xdg.rs               # XDG compliance validator
│       ├── venv.rs              # Virtual environment validator
│       ├── paths.rs             # Hardcoded path detector
│       ├── federation.rs        # Federation pattern validator
│       └── docs.rs              # Documentation structure validator
└── paths.rs                     # Existing XDG path utilities (reuse)
```

### Core Data Structures

```rust
// src/repo/mod.rs

pub struct ComplianceReport {
    pub repo_path: PathBuf,
    pub scan_time: DateTime<Utc>,
    pub violations: Vec<Violation>,
    pub severity: Severity,
    pub summary: ComplianceSummary,
}

pub struct Violation {
    pub file_path: PathBuf,
    pub line_number: Option<usize>,
    pub rule_id: String,
    pub severity: Severity,
    pub message: String,
    pub suggestion: Option<String>,
    pub auto_fixable: bool,
}

#[derive(PartialEq, Eq, PartialOrd, Ord)]
pub enum Severity {
    Info,
    Warning,
    Error,
    Critical,
}

pub struct ComplianceSummary {
    pub total_files_scanned: usize,
    pub violations_by_severity: HashMap<Severity, usize>,
    pub violations_by_standard: HashMap<String, usize>,
    pub compliance_percentage: f32,
}

pub trait Validator {
    fn name(&self) -> &str;
    fn validate(&self, repo_path: &Path) -> Result<Vec<Violation>>;
    fn can_auto_fix(&self, violation: &Violation) -> bool;
    fn auto_fix(&self, violation: &Violation, dry_run: bool) -> Result<FixResult>;
}

pub enum FixResult {
    Applied { before: String, after: String },
    DryRun { before: String, after: String },
    Failed { reason: String },
    Skipped { reason: String },
}
```

### Exit Codes

```rust
pub enum ExitCode {
    Success = 0,           // All checks passed
    Warnings = 1,          // Warnings found (non-strict mode)
    Errors = 2,            // Errors found
    Critical = 3,          // Critical violations
    InternalError = 4,     // Tool error
}
```

---

## Implementation Phases

### Phase 1: Foundation (Week 1)

**Goal**: Read-only validation with exit codes

**Deliverables:**
- ✅ Command structure in main.rs
- ✅ `repo::check()` implementation
- ✅ XDG validator (reuse paths.rs logic)
- ✅ Hardcoded path detector
- ✅ Text output format
- ✅ Exit code compliance

**Testing:**
```bash
# Should pass (0 exit code)
nabi repo align check ~/nabia/core/nabi-cli

# Should fail with violations (2 exit code)
nabi repo align check ~/nabia/platform/tools/legacy-tool

# JSON output for CI/CD
nabi repo align check --format json > compliance.json
```

### Phase 2: Reporting (Week 2)

**Goal**: Comprehensive human-readable reports

**Deliverables:**
- ✅ `repo::report()` implementation
- ✅ Grouped violation output
- ✅ Markdown report generation
- ✅ JSON report for tooling
- ✅ Severity-based filtering

**Testing:**
```bash
# Generate markdown report
nabi repo align report --output COMPLIANCE_REPORT.md

# Grouped by file
nabi repo align report --grouped

# Specific standard validation
nabi repo align validate --standard xdg
```

### Phase 3: Auto-Remediation (Week 3)

**Goal**: Safe automated fixes with backup

**Deliverables:**
- ✅ `repo::fix()` implementation
- ✅ Dry-run mode (preview changes)
- ✅ Interactive confirmation
- ✅ Automatic backup creation
- ✅ Common fix templates:
  - Path variable expansion (`/Users/tryk` → `~`)
  - XDG variable injection
  - Venv path correction

**Testing:**
```bash
# Preview fixes
nabi repo align fix --dry-run

# Interactive mode (confirm each fix)
nabi repo align fix

# Auto-apply safe fixes
nabi repo align fix --yes

# No backup (advanced)
nabi repo align fix --no-backup
```

### Phase 4: Integration (Week 4)

**Goal**: Git hooks and CI/CD integration

**Deliverables:**
- ✅ Git pre-commit hook template
- ✅ GitHub Actions workflow example
- ✅ CI/CD exit code documentation
- ✅ Hook auto-install command

**Example Git Hook:**
```bash
#!/bin/bash
# .git/hooks/pre-commit
nabi repo align check --strict || {
    echo "❌ Repository alignment check failed"
    echo "Run: nabi repo align report"
    exit 1
}
```

**Example GitHub Actions:**
```yaml
name: Repository Compliance

on: [push, pull_request]

jobs:
  compliance:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Install nabi CLI
        run: |
          # Installation steps
      - name: Validate Compliance
        run: nabi repo align check --strict --format json
```

---

## Reusable Components

### From Existing Codebase

**XDG Path Utilities** (`src/paths.rs`):
```rust
// Already implemented - reuse directly
impl NabiPaths {
    pub fn config_dir() -> Result<PathBuf>
    pub fn data_dir() -> Result<PathBuf>
    pub fn cache_dir() -> Result<PathBuf>
    pub fn state_dir() -> Result<PathBuf>
    pub fn bin_dir() -> Result<PathBuf>
}
```

**Manifest Validation** (existing `nabi docs manifest validate`):
- SHA256 integrity checking
- Drift detection logic
- File scanning patterns

**Link Mapper Rules** (`~/Sync/docs/.ops/validation/validation_rules.yaml`):
- Port all rules to Rust structs
- Reuse regex patterns
- Maintain exception logic

---

## File Discovery Patterns

### Scan Targets

```rust
pub struct ScanConfig {
    /// File patterns to include
    pub include_patterns: Vec<String>,  // ["*.md", "*.toml", "*.yaml", "*.sh"]

    /// File patterns to exclude
    pub exclude_patterns: Vec<String>,  // [".git/*", "target/*", "node_modules/*"]

    /// Directories to skip
    pub skip_dirs: Vec<String>,         // [".git", "target", ".cache"]

    /// Maximum file size (bytes)
    pub max_file_size: usize,           // 10MB default
}
```

### Default Configuration

```toml
# ~/.config/nabi/repo-align.toml

[scan]
include_patterns = [
    "*.md",
    "*.toml",
    "*.yaml",
    "*.yml",
    "*.sh",
    "*.bash",
    "*.zsh",
    "*.py",
    "*.rs",
    "Makefile",
    "Taskfile",
]

exclude_patterns = [
    ".git/*",
    "target/*",
    "node_modules/*",
    ".venv/*",
    "__pycache__/*",
    "*.pyc",
]

skip_dirs = [".git", "target", "node_modules", ".venv", "__pycache__"]

max_file_size = 10485760  # 10MB
```

---

## Auto-Fix Templates

### Common Replacements

```rust
pub struct FixTemplate {
    pub name: String,
    pub pattern: Regex,
    pub replacement: String,
    pub safe: bool,  // Can auto-apply without confirmation
}

// Example templates
let templates = vec![
    FixTemplate {
        name: "expand_user_path".to_string(),
        pattern: Regex::new(r"/Users/tryk/").unwrap(),
        replacement: "~/".to_string(),
        safe: true,
    },
    FixTemplate {
        name: "venv_location".to_string(),
        pattern: Regex::new(r"\.venv/").unwrap(),
        replacement: "~/.nabi/venvs/{tool-name}/".to_string(),
        safe: false,  // Requires manual confirmation (tool name varies)
    },
    FixTemplate {
        name: "xdg_config_injection".to_string(),
        pattern: Regex::new(r"~/\.config/nabi/").unwrap(),
        replacement: "$XDG_CONFIG_HOME/nabi/".to_string(),
        safe: true,
    },
];
```

---

## Testing Strategy

### Unit Tests

```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_xdg_validator_detects_hardcoded_paths() {
        let content = "/Users/tryk/nabia/tools/riff-cli";
        let violations = detect_hardcoded_paths(content);
        assert_eq!(violations.len(), 1);
        assert_eq!(violations[0].rule_id, "no_hardcoded_users");
    }

    #[test]
    fn test_venv_validator_detects_project_local() {
        let content = ".venv/bin/python";
        let violations = detect_venv_violations(content);
        assert!(violations.iter().any(|v| v.rule_id == "venv_location"));
    }

    #[test]
    fn test_auto_fix_path_expansion() {
        let before = "/Users/tryk/nabia";
        let after = apply_fix("expand_user_path", before);
        assert_eq!(after, "~/nabia");
    }
}
```

### Integration Tests

```rust
#[test]
fn test_check_command_compliant_repo() {
    let output = Command::new("nabi")
        .args(&["repo", "align", "check", "test_fixtures/compliant_repo"])
        .output()
        .expect("failed to execute");

    assert!(output.status.success());
    assert_eq!(output.status.code(), Some(0));
}

#[test]
fn test_check_command_non_compliant_repo() {
    let output = Command::new("nabi")
        .args(&["repo", "align", "check", "test_fixtures/drift_repo"])
        .output()
        .expect("failed to execute");

    assert!(!output.status.success());
    assert_eq!(output.status.code(), Some(2)); // Errors found
}
```

### Test Fixtures

```
~/nabia/core/nabi-cli/tests/fixtures/
├── compliant_repo/          # 100% compliant
│   ├── README.md
│   ├── manifest.toml
│   └── docs/
├── drift_repo/              # Has violations
│   ├── README.md           # Contains hardcoded paths
│   ├── setup.sh            # Uses .venv/
│   └── config.toml         # Missing XDG variables
└── mixed_repo/             # Some violations, some compliant
```

---

## Dependencies

### Cargo.toml Additions

```toml
[dependencies]
# ... existing dependencies ...

# For regex pattern matching
regex = "1.10"

# For file walking
walkdir = "2.4"

# For YAML parsing (validation rules)
serde_yaml = "0.9"

# For TOML parsing (config)
toml = "0.8"

# For colored output (already present)
colored = "2.0"
```

---

## Documentation Requirements

### User-Facing Documentation

1. **Command Reference**: Add to `~/nabia/core/nabi-cli/README.md`
2. **Examples**: Create `~/docs/tools/nabi-repo-align.md`
3. **CI/CD Integration Guide**: Add to federation docs
4. **Git Hook Templates**: Provide ready-to-use hooks

### Developer Documentation

1. **Architecture Overview**: This document
2. **Validator Development Guide**: How to add new validators
3. **Fix Template Guide**: How to create auto-fix patterns
4. **Testing Guide**: How to test validators

---

## Success Criteria

### Phase 1 (MVP)
- [x] Command structure implemented
- [ ] XDG and path validators working
- [ ] Exit codes correct for CI/CD
- [ ] Basic text output readable
- [ ] 80%+ test coverage

### Phase 2 (Enhanced Reporting)
- [ ] Markdown reports generated
- [ ] JSON output parseable
- [ ] Grouped violations clear
- [ ] Severity levels working

### Phase 3 (Auto-Remediation)
- [ ] Dry-run mode accurate
- [ ] Interactive mode UX smooth
- [ ] Backup creation reliable
- [ ] Safe fixes auto-applied correctly

### Phase 4 (Integration)
- [ ] Git hook example tested
- [ ] GitHub Actions workflow validated
- [ ] Documentation complete
- [ ] Federation-wide adoption

---

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| False positives in path detection | High | Comprehensive exception handling, test fixtures |
| Auto-fix breaking code | Critical | Mandatory dry-run preview, backup creation |
| Performance on large repos | Medium | Parallel file scanning, configurable limits |
| Regex pattern maintenance | Low | Centralized rule definitions, YAML config |

---

## Future Enhancements

1. **Custom Rule Definitions**: User-defined validation rules
2. **Watch Mode**: Continuous validation on file changes
3. **VS Code Extension**: Real-time compliance feedback
4. **Auto-Fix Suggestions**: AI-powered fix recommendations
5. **Compliance Badges**: Generate badges for README.md
6. **Historical Tracking**: Compliance score over time

---

## References

- **Linear Issue**: [NOS-671](https://linear.app/nabia/issue/NOS-671)
- **Validation Rules**: `~/Sync/docs/.ops/validation/validation_rules.yaml`
- **Manifest System**: `nabi docs manifest --help`
- **Link Mapper**: `~/Sync/docs/.ops/scripts/link_audit.py`
- **XDG Specification**: https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html

---

**Status**: Ready for Phase 1 implementation
**Next Step**: Create `src/repo/` module and implement `check` command

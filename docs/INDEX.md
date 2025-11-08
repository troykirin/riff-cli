# riff-cli Visualization Module Documentation

**Status**: Complete and Production-Ready
**Last Updated**: 2025-11-08
**Total Documents**: 4 MDX files + index

---

## Documentation Structure

### 1. Quick Start Guide
**File**: `visualization-module-quickstart.mdx`
**Length**: ~350 lines
**Audience**: All users (developers, operators)

Quick introduction to the visualization module with three ways to use it:
- Visualize existing JSONL files
- Search with inline visualization
- Search and save results

Includes troubleshooting, workflows, and architecture overview.

**Read this first if**: You want to start using visualization immediately.

---

### 2. JSONL Specification
**File**: `jsonl-specification.mdx`
**Length**: ~500 lines
**Audience**: Developers, integrators

Complete technical specification for the JSONL data format:
- Node record structure
- Edge record structure
- Validation rules
- Field constraints
- Generation patterns
- Consumption patterns
- Extensibility rules

Includes detailed examples, error handling, and size guidelines.

**Read this if**: You need to understand or work with the data format.

---

### 3. API Reference
**File**: `api-reference.mdx`
**Length**: ~450 lines
**Audience**: Developers

Complete API documentation for the visualization module:
- RiffDagTUIHandler class (4 methods)
- Formatter functions (3 functions)
- CLI integration patterns
- Type annotations
- Error handling patterns
- Performance characteristics

Includes code examples and integration guides.

**Read this if**: You're integrating visualization into your own code.

---

### 4. Real-World Examples
**File**: `examples.mdx`
**Length**: ~400 lines
**Audience**: All users

11 real-world usage scenarios:
1. Quick search visualization
2. Export for later analysis
3. Large dataset analysis
4. Multi-step investigation
5. Compare multiple searches
6. Validate and repair JSONL
7. Programmatic usage (Python)
8. Custom data visualization
9. CLI scripting
10. Troubleshooting workflow
11. Batch visualization

Plus performance tips and common patterns.

**Read this if**: You want practical examples of using the module.

---

## Quick Navigation

### By Use Case

**I want to search and visualize immediately**
→ Quick Start → Example 1

**I want to understand the data format**
→ JSONL Specification

**I want to integrate visualization into my app**
→ API Reference + Example 7

**I want to validate/debug JSONL files**
→ JSONL Specification (Validation Rules) + Example 6

**I want to analyze large datasets**
→ Quick Start + Example 3

**I want to archive and compare searches**
→ Examples 2, 4, 5, 11

**Something's broken, help!**
→ Quick Start (Troubleshooting) + Example 10

---

### By Audience

**End Users (riff-cli commands)**
- Quick Start Guide
- Examples 1-5, 9-11

**Developers (Python integration)**
- API Reference
- Examples 7-8
- JSONL Specification

**Operators (deployment, validation)**
- Quick Start (Installation)
- Examples 6, 10, 11
- JSONL Specification (Validation)

**Data Engineers (custom data)**
- JSONL Specification
- Examples 8, 11

---

## Documentation Statistics

| Document | Lines | Sections | Code Examples | Tables |
|----------|-------|----------|---------------|--------|
| Quick Start | 350 | 15 | 12 | 3 |
| JSONL Spec | 500 | 18 | 25 | 8 |
| API Reference | 450 | 16 | 20 | 4 |
| Examples | 400 | 11 | 18 | 1 |
| **TOTAL** | **1,700** | **60** | **75** | **16** |

---

## Key Topics Covered

### Visualization Workflows
- Search + instant visualization
- Export for later reuse
- Multi-step investigations
- Comparative analysis

### Technical Specifications
- JSONL format (complete spec)
- Node and edge records
- Field constraints
- Validation rules

### Integration Patterns
- CLI commands
- Programmatic Python API
- Subprocess orchestration
- Error handling

### Practical Examples
- Individual use cases
- Batch operations
- Custom data visualization
- Troubleshooting

### Performance & Scalability
- Large dataset handling (1000+ nodes)
- Performance characteristics
- Memory usage
- Optimization tips

---

## File Locations

```
~/nabia/tools/riff-cli/
├── docs/
│   ├── INDEX.md                            (THIS FILE)
│   ├── visualization-module-quickstart.mdx
│   ├── jsonl-specification.mdx
│   ├── api-reference.mdx
│   └── examples.mdx
├── src/riff/visualization/
│   ├── __init__.py
│   ├── handler.py
│   └── formatter.py
└── tests/
    ├── unit/
    │   ├── test_visualization_handler.py
    │   └── test_visualization_formatter.py
    └── integration/
        └── test_visualization_workflow.py
```

---

## Format Notes

All documentation files use:
- **Format**: MDX (Markdown with JSX)
- **Encoding**: UTF-8
- **Line endings**: LF (Unix)
- **Frontmatter**: YAML metadata

**Frontmatter includes**:
- `title`: Document title
- `description`: Brief summary
- `author`: Author name
- `date`: Last updated date
- `category`: Documentation category
- `tags`: Search tags
- `audience`: Target audience (💻 dev, 🔧 ops)
- `status`: Active/Draft/Archived

---

## Document Relationships

```
Quick Start (entry point)
    │
    ├─→ API Reference (for developers)
    │   └─→ Examples (real code)
    │
    ├─→ JSONL Specification (for data format)
    │   └─→ Examples (format examples)
    │
    └─→ Examples (for inspiration)
        └─→ JSONL Spec or API Reference (for details)
```

---

## Quality Checklist

- [x] All code examples tested and working
- [x] Cross-references verified
- [x] YAML frontmatter valid
- [x] Markdown syntax correct
- [x] Audience clearly marked
- [x] Examples match actual implementation
- [x] API docs match actual code
- [x] JSONL spec matches validator
- [x] No broken links
- [x] Performance claims verified

---

## Version Information

**Documentation Version**: 1.0
**Module Version**: 1.0
**Python Version**: 3.13+
**Last Updated**: 2025-11-08

---

## How to Use This Documentation

### For Reading
1. **Start with**: Quick Start Guide
2. **For details**: API Reference or JSONL Specification
3. **For inspiration**: Examples section
4. **For validation**: JSONL Specification validation rules

### For Searching
Use document titles and tags:
- `visualization` - All visualization docs
- `jsonl` - Format specification
- `api` - API reference
- `examples` - Real-world scenarios
- `quickstart` - Getting started

### For Contributing
To update documentation:
1. Maintain YAML frontmatter
2. Keep code examples working
3. Update cross-references
4. Test all examples
5. Update this INDEX.md

---

## Support

For questions or issues:
1. **First**: Check the Quick Start troubleshooting section
2. **Then**: Search Examples for similar use case
3. **Next**: Refer to API Reference or JSONL Specification
4. **Finally**: Report issue with reproducible example

---

*Complete documentation for riff-cli Visualization Module v1.0*
*Ready for publication and distribution*

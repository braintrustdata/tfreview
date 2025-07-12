# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TFReview is a Python tool that converts Terraform plan output into an interactive HTML interface for easier review. The project uses a simple 3-module architecture with CLI entry point, parser, and HTML renderer.

## Key Commands

### Development Setup
```bash
# Install development dependencies
make install-dev
# Or manually: pip install -e ".[dev]"

# Install package only
make install
```

### Testing
```bash
# Run tests
make test
# Or: pytest tests/ -v

# Run tests with coverage
make test-cov
# Or: pytest tests/ -v --cov=tfreview --cov-report=html --cov-report=term
```

### Code Quality
```bash
# Run linting (flake8 + mypy)
make lint

# Format code
make format

# Check formatting without changes
make format-check
```

### Demo and Testing
```bash
# Run demo with sample plan
make demo

# Test all sample plans
make test-all-samples
```

### Build and Distribution
```bash
# Clean build artifacts
make clean

# Build package
make build
```

## Code Architecture

### Core Modules (tfreview/)
- **`cli.py`**: Command-line interface with argparse, handles stdin/file input, strips ANSI codes
- **`parser.py`**: Terraform plan text parser using regex patterns, converts to structured data classes
- **`renderer.py`**: HTML generator using Jinja2 templates, applies syntax highlighting and interactive features

### Data Flow
1. CLI reads terraform plan text (stdin or file)
2. TerraformPlanParser converts text to PlanSummary dataclass with ResourceChange objects
3. HTMLRenderer uses Jinja2 templates to generate interactive HTML with embedded CSS/JS

### Key Data Structures
- `PlanSummary`: Main container with resource changes, output changes, and summary counts
- `ResourceChange`: Individual resource with change type, attributes, and metadata
- `ChangeType` enum: CREATE, UPDATE, DELETE, REPLACE, NO_OP

### Templates (templates/)
- **`modern.html`**: Standalone HTML template with embedded CSS/JS for interactive review interface
- **`standalone.html`**: Alternative template option

### Testing
- Tests located in `tests/` directory
- Test files: `test_parser.py`, `test_renderer.py`
- Sample plans in `samples/` directory for testing different scenarios

## Important Patterns

### Parser Regex Patterns
The parser uses specific regex patterns to identify Terraform plan sections:
- Change headers: `# resource will be action` or `# resource must be action`
- Attribute changes: `+`, `-`, `~` prefixes for add/delete/modify
- Replacement patterns: `-/+` or `+/-` for force replacement

### HTML Rendering Features
- Collapsible resource sections with expand/collapse
- Syntax highlighting for terraform diff output
- Review tracking (approve/needs-changes) with local storage
- Progress tracking with visual indicators

### Entry Point
Main CLI entry point is `tfreview.cli:main` configured in setup.py console_scripts.

## Development Notes

- Package uses `uv` for installation as mentioned in README
- Built entirely with AI assistance as noted in README
- Templates use Jinja2 with custom filters for terraform syntax highlighting
- No external CSS/JS dependencies - everything embedded in templates
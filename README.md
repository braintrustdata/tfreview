# TFReview 🔍

A modern, interactive tool for reviewing Terraform plans in a beautiful HTML interface.

![TFReview Demo](https://img.shields.io/badge/demo-coming_soon-blue)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

## Features ✨

- **Interactive HTML Interface**: Review terraform plans in a modern, user-friendly web interface
- **Collapsible Resource Views**: Organize changes with expandable sections for each resource
- **Review Tracking**: Mark resources as approved or needing changes with progress tracking
- **Syntax Highlighting**: Color-coded terraform diff output for easy reading
- **Navigation Controls**: Keyboard shortcuts and buttons to navigate between changes
- **Responsive Design**: Works great on desktop and mobile devices
- **Multiple Input Methods**: Read from files or stdin
- **JSON Export**: Export parsed plan data as JSON for integration with other tools

## Installation 📦

### Using pip

```bash
pip install tfreview
```

### From source

```bash
git clone https://github.com/tfreview/tfreview.git
cd tfreview
pip install -e .
```

### Development installation

```bash
git clone https://github.com/tfreview/tfreview.git
cd tfreview
pip install -e ".[dev]"
```

## Quick Start 🚀

### Basic Usage

```bash
# Review a terraform plan file
terraform plan -out=tfplan
terraform show tfplan | tfreview -

# Or save plan to text file first
terraform show tfplan > plan.txt
tfreview plan.txt
```

### Command Line Options

```bash
# Specify output file
tfreview plan.txt -o my-review.html

# Don't open browser automatically
tfreview plan.txt --no-browser

# Output as JSON instead of HTML
tfreview plan.txt --json

# Use custom templates
tfreview plan.txt --templates /path/to/custom/templates
```

### Reading from stdin

```bash
terraform plan | tfreview -
```

## Interface Guide 🎯

### Main Features

1. **Summary Header**: Shows counts of resources to add, change, and destroy
2. **Progress Tracker**: Displays review progress with a visual progress bar
3. **Resource Cards**: Each resource change is displayed in a collapsible card
4. **Review Actions**: Approve, mark as needing changes, or navigate to next resource

### Keyboard Shortcuts

- **`n`**: Jump to next unreviewed resource
- **Click headers**: Expand/collapse resource details

### Review Workflow

1. Open the HTML file in your browser
2. Review each resource change by clicking on the headers
3. Use the action buttons to:
   - ✅ **Approve**: Mark the change as reviewed and acceptable
   - ⚠️ **Needs Changes**: Mark the change as requiring modifications
   - ⏭️ **Next Change**: Navigate to the next resource
4. Track your progress with the progress bar at the top

## Supported Terraform Features 🛠️

- ✅ Resource creation, updates, and deletion
- ✅ Resource replacements (destroy + create)
- ✅ Module resources (nested modules supported)
- ✅ Indexed resources (e.g., `aws_instance.web[0]`)
- ✅ Data sources
- ✅ Sensitive values detection
- ✅ Computed values highlighting
- ✅ Output changes
- ✅ Complex nested attributes

## Examples 📋

### Sample Output Types

TFReview handles various terraform plan scenarios:

1. **Basic Changes**: Simple create/update/delete operations
2. **Module Resources**: Resources defined in modules
3. **No Changes**: Clean "no changes" detection
4. **Complex Plans**: Nested modules, indexed resources, data sources
5. **Sensitive Data**: Proper handling of sensitive values

### Integration Examples

```bash
# CI/CD Pipeline Integration
terraform plan -out=tfplan
terraform show tfplan | tfreview - -o plan-review.html --no-browser

# Team Review Process
terraform plan > plan.txt
tfreview plan.txt -o team-review.html
# Share team-review.html with your team

# JSON Export for Automation
terraform plan | tfreview - --json > plan-data.json
```

## API Reference 📚

### TerraformPlanParser

```python
from tfreview import TerraformPlanParser

parser = TerraformPlanParser()
plan_summary = parser.parse(plan_text)
json_output = parser.to_json(plan_summary)
```

### HTMLRenderer

```python
from tfreview import HTMLRenderer

renderer = HTMLRenderer()
html_content = renderer.create_standalone_html(plan_summary)
```

## Development 🔧

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
# Format code
black tfreview/

# Lint code
flake8 tfreview/

# Type checking
mypy tfreview/
```

### Project Structure

```
tfreview/
├── tfreview/           # Main package
│   ├── __init__.py
│   ├── parser.py       # Terraform plan parser
│   ├── renderer.py     # HTML renderer
│   └── cli.py          # Command line interface
├── templates/          # HTML templates
│   └── standalone.html
├── samples/            # Sample terraform plans for testing
├── tests/              # Test suite
└── README.md
```

## Contributing 🤝

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Contribution Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make changes and add tests
4. Run tests: `pytest`
5. Submit a pull request

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Roadmap 🗺️

- [ ] **Custom Themes**: Support for custom CSS themes
- [ ] **Export Options**: PDF and other export formats
- [ ] **Team Features**: Collaborative review features
- [ ] **CI/CD Integration**: GitHub Actions and other CI/CD platforms
- [ ] **Advanced Filtering**: Filter resources by type, module, etc.
- [ ] **Diff Comparison**: Compare multiple plan versions

## Support 💬

- 📖 [Documentation](https://github.com/tfreview/tfreview/wiki)
- 🐛 [Bug Reports](https://github.com/tfreview/tfreview/issues)
- 💡 [Feature Requests](https://github.com/tfreview/tfreview/issues)
- 💬 [Discussions](https://github.com/tfreview/tfreview/discussions)

## Acknowledgments 🙏

- Inspired by the need for better terraform plan review processes
- Built with modern web technologies for the best user experience
- Thanks to all contributors and the Terraform community

---

Made with ❤️ for the DevOps community
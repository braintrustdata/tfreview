# TFReview 🔍

A modern, interactive tool for reviewing Terraform plans in a beautiful HTML interface.

## Features ✨

- **Interactive HTML Interface**: Review terraform plans in a modern, user-friendly web interface
- **Collapsible Resource Views**: Organize changes with expandable sections for each resource
- **Review Tracking**: Mark resources as approved or needing changes with progress tracking
- **Syntax Highlighting**: Color-coded terraform diff output for easy reading
- **Navigation Controls**: Keyboard shortcuts and buttons to navigate between changes
- **Responsive Design**: Works great on desktop and mobile devices
- **Multiple Input Methods**: Read from files or stdin
- **JSON Export**: Export parsed plan data as JSON for integration with other tools

## Screenshots
![CleanShot 2025-06-19 at 14 41 29@2x](https://github.com/user-attachments/assets/7a24b08c-6d45-4d48-a43c-975ea80bccea)
![CleanShot 2025-06-19 at 14 37 22](https://github.com/user-attachments/assets/214c19d6-f1ad-493a-83ff-490e3b66a3cc)


## Installation 📦

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

```bash
terraform plan | tfreview -
```

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

```

## Development 🔧

### Running Tests

```bash
pytest tests/
```

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

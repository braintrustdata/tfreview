# TFReview 🔍

View your Terraform plan in an beautiful and easy to use HTML interface.

Staring at reams of monospace text in a terminal is so 1985. TFReview blasts terraform into the future! (the late 90s)

Pipe your terraform plan output to it and it will open something readable by humans in a browser.
`terraform plan | tfreview`

![TFReview Screenshot](assets/tfreview.png)

https://github.com/user-attachments/assets/a7897be5-be19-42dd-bb01-26ed9548ddf8

## Features ✨

- **Interactive HTML Interface**: Review terraform plans in a modern, user-friendly web interface
- **Collapsible Resource Views**: Organize changes with expandable sections for each resource
- **Review Tracking**: Mark resources as approved or needing changes with progress tracking (browser local)
- **Syntax Highlighting**: Color-coded terraform diff output for easier reading
- **Entirely built using AI**: Please god, don't look at the commit history.

## Installation 📦

### From source

```bash
git clone https://github.com/tfreview/tfreview.git
cd tfreview
pip install -e .
```

## Quick Start 🚀

### Basic Usage

```bash
# Review a terraform plan file
terraform plan -no-color | tfreview
terraform show tfplan | tfreview

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
```


## Development 🔧

### Running Tests

```bash
pytest tests/
```

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Roadmap 🗺️

- [ ] **CI/CD Integration**: GitHub Action to run and post results to a PR as clickable comment

# Credits
Cursor did all of this. Vibe coding is insanely frustrating, but I never would have created this myself without it. Apologies for the code. This isn't a work of art I carefully crafted and reviewed. I just wanted it to exist so that reviewing large terraform plans can now be humanly possible.

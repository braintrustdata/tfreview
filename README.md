# TFReview

View your Terraform plan in an beautiful and easy to use HTML interface.

Staring at reams of monospace text in a terminal is so 1985. Let TFReview blast your terraform experience into a modern future! (the late 90s)

Pipe your terraform plan output to it and it will open something readable by humans in a browser:

`terraform plan | tfreview`

![TFReview Screenshot](assets/tfreview.png)

https://github.com/user-attachments/assets/308543e0-939a-422a-977e-c3e4bb098e77

## Features

- **Collapsible Resource Views**: Organize changes with expandable sections for each resource
- **Upload to an S3 static website**: Make your plans clickable and sharable
- **Syntax Highlighting**: Color-coded terraform diff output for easier reading
- **Review Tracking**: Mark resources as approved or needing changes with progress tracking (browser local)
- **Easy Review Workflow**: Read, Click, Read, Click, Read, Click
- **Entirely built using AI**: I beg you not to look at the commit history.

## Installation
Requires `uv` to be [installed](https://docs.astral.sh/uv/getting-started/installation/).

### Try it out without installing
`uvx` invokes in a temporary environment without installing anything permenently

```bash
alias tfreview="uvx --from git+https://github.com/braintrustdata/tfreview@main tfreview"
terraform plan | tfreview
```

### Install from source
```bash
uv tool install --from git+https://github.com/braintrustdata/tfreview@main tfreview
tfreview --help
```

## Quick Start

### Basic Usage

```bash
# Review a terraform plan file
terraform plan | tfreview
terraform show tfplan.out | tfreview

# Or save plan to text file first
terraform show tfplan > plan.txt
tfreview plan.txt

# Upload to an S3 bucket with static website and custom domain name
terraform plan | tfreview --s3-path=s3://mybucket/ --s3-website-url=https://mysite.com
# Plan available at: https://mysite.com/37369285bd6eb38db0bd3c9824e2994c.html
```

### Command Line Options

```bash
TFReview - Review Terraform plans in a nice HTML interface

positional arguments:
  input                 Terraform plan file to review (default: stdin)

options:
  -h, --help            show this help message and exit
  -o OUTPUT, --output OUTPUT
                        Output HTML file (default: .terraform/tfreview-plan.html)
  --no-browser          Don't open browser automatically
  --template TEMPLATE   Template file to use (default: modern.html)
  --s3-path S3_PATH     Upload to S3 at the specified path (e.g., s3://mybucket/tfplans/)
  --s3-website-url S3_WEBSITE_URL
                        S3 static website URL (e.g., http://mysite.com). Used instead of default S3 URL when specified.
  --atlantis            Enable Atlantis mode: use BASE_REPO_OWNER/BASE_REPO_NAME/PROJECT_NAME in S3 path and display PULL_URL/PROJECT_NAME in HTML
  --version             show program's version number and exit

Examples:
  # Read from stdin (default)
  terraform plan | tfreview

  # Review a terraform plan file
  tfreview plan.txt

  # Specify output file
  tfreview -o review.html

  # Don't open browser automatically
  tfreview --no-browser

  # Upload to S3
  terraform plan | tfreview --s3-path=s3://mybucket/tfplans/

  # Upload to S3 with custom website URL
  terraform plan | tfreview --s3-path=s3://mybucket/tfplans/ --s3-website-url=http://mysite.com

  # Upload to S3 without opening browser
  terraform plan | tfreview --s3-path=s3://mybucket/tfplans/ --no-browser
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

# Credits
Built entirely with AI in Cursor using plain english. The code quality matches my will to live after reviewing thousands of Terraform plans manually. Technically functional but deeply concerning. You're welcome.

Seriously though, as horribly frustrating vibe coding is, I never would have built this myself without it. Vibe coding solved a long standing problem for me for $20/month (+ some mental anguish).

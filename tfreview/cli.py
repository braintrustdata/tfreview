import argparse
import sys
import webbrowser
import re
import hashlib
import os
from pathlib import Path
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .parser import PlanSummary

# Handle both package and direct script execution
try:
    from .parser import TerraformPlanParser
    from .renderer import HTMLRenderer
except ImportError:
    # Fallback for direct script execution
    import os

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from tfreview.parser import TerraformPlanParser
    from tfreview.renderer import HTMLRenderer


def strip_ansi_codes(text: str) -> str:
    """Remove ANSI escape codes from text."""
    # Pattern to match ANSI escape sequences
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def calculate_checksum(text: str) -> str:
    """Calculate SHA256 checksum of text (first 16 characters)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def format_plan_summary(plan_summary: "PlanSummary") -> str:
    """Format plan summary in Terraform style: 'Plan: X to add, Y to change, Z to destroy.'"""
    parts = []

    if plan_summary.to_add > 0:
        parts.append(f"{plan_summary.to_add} to add")
    if plan_summary.to_change > 0:
        parts.append(f"{plan_summary.to_change} to change")
    if plan_summary.to_replace > 0:
        parts.append(f"{plan_summary.to_replace} to replace")
    if plan_summary.to_destroy > 0:
        parts.append(f"{plan_summary.to_destroy} to destroy")

    if parts:
        return f"Plan: {', '.join(parts)}."
    else:
        return "Plan: No changes."


def upload_to_s3(
    html_content: str,
    s3_path: str,
    plan_text: str,
    s3_website_url: Optional[str] = None,
    atlantis: bool = False,
) -> str:
    """
    Upload HTML content to S3.

    Args:
        html_content: The HTML content to upload
        s3_path: S3 path (e.g., s3://mybucket/tfplans/)
        plan_text: The original plan text for checksum calculation
        s3_website_url: Optional static website URL

    Returns:
        The URL to access the uploaded file

    Raises:
        ValueError: If S3 path is invalid
        Exception: If credentials are invalid or upload fails
    """
    try:
        import boto3
        from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError
    except ImportError:
        print("Error: boto3 is required for S3 upload. Install with: pip install boto3", file=sys.stderr)
        sys.exit(1)

    # Parse S3 path
    if not s3_path.startswith("s3://"):
        raise ValueError("S3 path must start with s3://")

    path_parts = s3_path[5:].split("/", 1)
    bucket_name = path_parts[0]
    prefix = path_parts[1] if len(path_parts) > 1 else ""

    # Ensure prefix ends with / if it exists
    if prefix and not prefix.endswith("/"):
        prefix += "/"

    # If atlantis mode, construct path from environment variables
    if atlantis:
        base_repo_owner = os.environ.get("BASE_REPO_OWNER", "")
        base_repo_name = os.environ.get("BASE_REPO_NAME", "")
        project_name = os.environ.get("PROJECT_NAME", "")

        # Build the atlantis path structure
        atlantis_path_parts = []
        if base_repo_owner:
            atlantis_path_parts.append(base_repo_owner)
        if base_repo_name:
            atlantis_path_parts.append(base_repo_name)
        if project_name:
            atlantis_path_parts.append(project_name)

        if atlantis_path_parts:
            atlantis_prefix = "/".join(atlantis_path_parts) + "/"
            prefix = prefix + atlantis_prefix

    # Calculate checksum and create filename
    checksum = calculate_checksum(plan_text)
    filename = f"{checksum}.html"
    s3_key = f"{prefix}{filename}"

    # Initialize S3 client and check credentials
    try:
        s3_client = boto3.client("s3")
        # Test credentials by checking if bucket exists
        s3_client.head_bucket(Bucket=bucket_name)
    except (NoCredentialsError, PartialCredentialsError, ClientError) as e:
        print(f"Error checking bucket '{bucket_name}'. Please verify you have AWS credentials set.", file=sys.stderr)
        sys.exit(1)

    # Upload file
    try:
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=html_content.encode("utf-8"),
            ContentType="text/html",
        )
    except ClientError as e:
        print(f"Error: Failed to upload to S3: {e}", file=sys.stderr)
        sys.exit(1)

    # Construct URL
    if s3_website_url:
        # Use custom website URL
        base_url = s3_website_url.rstrip("/")
        url = f"{base_url}/{s3_key}"
    else:
        # Use standard S3 URL
        region = s3_client.get_bucket_location(Bucket=bucket_name).get("LocationConstraint")
        if region is None:
            region = "us-east-1"
        url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"

    return url


def main():
    parser = argparse.ArgumentParser(
        description="TFReview - Review Terraform plans in a nice HTML interface",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
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
        """,
    )

    parser.add_argument(
        "input",
        nargs="?",
        default="-",
        help="Terraform plan file to review (default: stdin)",
    )

    parser.add_argument(
        "-o",
        "--output",
        help="Output HTML file (default: .terraform/tfreview-plan.html)",
        default=".terraform/tfreview-plan.html",
    )

    parser.add_argument(
        "--no-browser", action="store_true", help="Don't open browser automatically"
    )

    parser.add_argument(
        "--template",
        help="Template file to use (default: modern.html)",
        default="modern.html",
    )

    parser.add_argument(
        "--s3-path",
        help="Upload to S3 at the specified path (e.g., s3://mybucket/tfplans/)",
        default=None,
    )

    parser.add_argument(
        "--s3-website-url",
        help="S3 static website URL (e.g., http://mysite.com). Used instead of default S3 URL when specified.",
        default=None,
    )

    parser.add_argument(
        "--atlantis",
        action="store_true",
        help="Enable Atlantis mode: use BASE_REPO_OWNER/BASE_REPO_NAME/PROJECT_NAME in S3 path and display PULL_URL/PROJECT_NAME in HTML",
    )

    parser.add_argument("--version", action="version", version="TFReview 1.0.0")

    args = parser.parse_args()

    try:
        if args.input == "-":
            # Try to read from stdin
            plan_text = ""
            try:
                # Check if stdin is connected to a terminal (interactive) vs pipe
                if sys.stdin.isatty():
                    # Interactive terminal - show help
                    parser.print_help()
                    sys.exit(0)
                else:
                    # Reading from pipe - read all input
                    for line in sys.stdin:
                        print(line, end="", flush=True)  # Echo to terminal
                        plan_text += line
            except (EOFError, KeyboardInterrupt):
                # No data available or interrupted
                parser.print_help()
                sys.exit(0)
        else:
            with open(args.input, "r", encoding="utf-8") as f:
                plan_text = f.read()

        plan_text = strip_ansi_codes(plan_text)

        if not plan_text:
            print("No plan found", file=sys.stderr)
            sys.exit(1)

        parser_instance = TerraformPlanParser()
        plan_summary = parser_instance.parse(plan_text)

        # Get Atlantis environment variables if --atlantis is set
        pull_url = None
        project_name = None
        if args.atlantis:
            pull_url = os.environ.get("PULL_URL")
            project_name = os.environ.get("PROJECT_NAME")

        renderer = HTMLRenderer()
        html_content = renderer.create_standalone_html(
            plan_summary, args.template, pull_url=pull_url, project_name=project_name
        )

        output_path = Path(args.output)
        # Create parent directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        # Handle S3 upload if requested
        if args.s3_path:
            url = upload_to_s3(
                html_content=html_content,
                s3_path=args.s3_path,
                plan_text=plan_text,
                s3_website_url=args.s3_website_url,
                atlantis=args.atlantis,
            )
            print(f"Plan Review URL: {url}")

            # In atlantis mode, also print the plan summary
            if args.atlantis:
                summary = format_plan_summary(plan_summary)
                print(summary)

            # Only open browser if website URL is provided and --no-browser is not set
            if args.s3_website_url and not args.no_browser:
                webbrowser.open(url)
        else:
            # Local file behavior
            if not args.no_browser:
                webbrowser.open(f"file://{output_path.absolute()}")
            else:
                print(f"Review Plan: {output_path.absolute()}")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error processing plan: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

import argparse
import sys
import webbrowser
import re
from pathlib import Path

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
        help="Output HTML file (default: plan_review.html)",
        default="plan_review.html",
    )

    parser.add_argument(
        "--no-browser", action="store_true", help="Don't open browser automatically"
    )

    parser.add_argument(
        "--template",
        help="Template file to use (default: modern.html)",
        default="modern.html",
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

        if not plan_summary.has_changes:
            sys.exit(0)

        renderer = HTMLRenderer()
        html_content = renderer.create_standalone_html(plan_summary, args.template)

        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

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

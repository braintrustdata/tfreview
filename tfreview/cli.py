"""
Command Line Interface for TFReview.
"""

import argparse
import sys
import webbrowser
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


def main():
    """Main CLI entry point."""
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

  # Use a custom template
  tfreview --template nextui_standalone.html

  # Use custom templates directory
  tfreview --templates /path/to/templates --template my_template.html

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
        "--json", action="store_true", help="Output parsed plan as JSON instead of HTML"
    )

    parser.add_argument("--templates", help="Custom templates directory")

    parser.add_argument(
        "--template",
        help="Template file to use (default: modern.html)",
        default="modern.html",
    )

    parser.add_argument("--version", action="version", version="TFReview 1.0.0")

    args = parser.parse_args()

    try:
        # Read input
        if args.input == "-":
            plan_text = ""
            for line in sys.stdin:
                print(line, end="", flush=True)  # Echo to terminal
                plan_text += line
        else:
            with open(args.input, "r", encoding="utf-8") as f:
                plan_text = f.read()

        if not plan_text:
            print("No plan found", file=sys.stderr)
            sys.exit(1)

        # Parse the plan
        print("\nParsing terraform plan...", file=sys.stderr)
        parser_instance = TerraformPlanParser()
        plan_summary = parser_instance.parse(plan_text)

        if args.json:
            # Output as JSON
            print(parser_instance.to_json(plan_summary))
            return

        # Render as HTML
        print("Generating HTML review...", file=sys.stderr)
        renderer = HTMLRenderer(args.templates)
        html_content = renderer.create_standalone_html(plan_summary, args.template)

        # Write output
        output_path = Path(args.output)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"Plan review generated: {output_path.absolute()}")

        # Open in browser unless disabled
        if not args.no_browser:
            webbrowser.open(f"file://{output_path.absolute()}")
            print("Opening in browser...")

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error processing plan: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

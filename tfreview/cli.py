"""
Command Line Interface for TFReview.
"""

import argparse
import sys
import webbrowser
from pathlib import Path
from .parser import TerraformPlanParser
from .renderer import HTMLRenderer


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='TFReview - Review Terraform plans in a nice HTML interface',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Review a terraform plan file
  tfreview plan.txt
  
  # Read from stdin
  terraform plan | tfreview -
  
  # Specify output file
  tfreview plan.txt -o review.html
  
  # Don't open browser automatically
  tfreview plan.txt --no-browser
        '''
    )
    
    parser.add_argument(
        'input',
        help='Terraform plan file to review (use "-" for stdin)'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Output HTML file (default: plan_review.html)',
        default='plan_review.html'
    )
    
    parser.add_argument(
        '--no-browser',
        action='store_true',
        help='Don\'t open browser automatically'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output parsed plan as JSON instead of HTML'
    )
    
    parser.add_argument(
        '--templates',
        help='Custom templates directory'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='TFReview 1.0.0'
    )
    
    args = parser.parse_args()
    
    try:
        # Read input
        if args.input == '-':
            plan_text = sys.stdin.read()
        else:
            with open(args.input, 'r', encoding='utf-8') as f:
                plan_text = f.read()
        
        # Parse the plan
        parser_instance = TerraformPlanParser()
        plan_summary = parser_instance.parse(plan_text)
        
        if args.json:
            # Output as JSON
            print(parser_instance.to_json(plan_summary))
            return
        
        # Render as HTML
        renderer = HTMLRenderer(args.templates)
        html_content = renderer.create_standalone_html(plan_summary)
        
        # Write output
        output_path = Path(args.output)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"Plan review generated: {output_path.absolute()}")
        
        # Open in browser unless disabled
        if not args.no_browser:
            webbrowser.open(f'file://{output_path.absolute()}')
            print("Opening in browser...")
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error processing plan: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
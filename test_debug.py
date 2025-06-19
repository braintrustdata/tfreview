#!/usr/bin/env python3

from tfreview.parser import TerraformPlanParser
import re

def debug_parser():
    parser = TerraformPlanParser()
    
    with open('test_user_plan.txt', 'r') as f:
        plan_text = f.read()
    
    print("=== Testing Parser with User's Plan ===")
    result = parser.parse(plan_text)
    
    print(f'Has changes: {result.has_changes}')
    print(f'To add: {result.to_add}, To change: {result.to_change}, To destroy: {result.to_destroy}')
    print(f'Resource changes found: {len(result.resource_changes)}')
    
    for rc in result.resource_changes:
        print(f'  - {rc.resource_address}: {rc.change_type}')
    
    print("\n=== Debug: Testing regex patterns ===")
    lines = plan_text.split('\n')
    
    # Test the change header pattern
    change_header_pattern = re.compile(r'^  # (.+?) will be (.+?)$')
    
    for i, line in enumerate(lines):
        if '# module.braintrust-data-plane' in line:
            print(f"Line {i}: '{line}'")
            match = change_header_pattern.match(line)
            if match:
                print(f"  MATCH: resource='{match.group(1)}', action='{match.group(2)}'")
            else:
                print(f"  NO MATCH")
                # Let's see what the line actually starts with
                print(f"  Line starts with: {repr(line[:10])}")
    
    # Check for no-changes pattern
    no_changes_pattern = re.compile(r'No changes\. Infrastructure is up-to-date\.')
    has_no_changes = any(no_changes_pattern.search(line) for line in lines)
    print(f"\nNo changes pattern detected: {has_no_changes}")
    
    # Check for summary line
    summary_pattern = re.compile(r'Plan: (\d+) to add, (\d+) to change, (\d+) to destroy')
    for line in lines:
        match = summary_pattern.search(line)
        if match:
            print(f"Summary found: {match.group(0)}")
            print(f"  Add: {match.group(1)}, Change: {match.group(2)}, Destroy: {match.group(3)}")

if __name__ == '__main__':
    debug_parser()
"""
Terraform Plan Parser - Parses terraform plan output into structured data.
"""

import re
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class ChangeType(Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    REPLACE = "replace"
    NO_OP = "no-op"


@dataclass
class AttributeChange:
    name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    is_sensitive: bool = False
    is_computed: bool = False


@dataclass
class ResourceChange:
    resource_address: str
    resource_type: str
    resource_name: str
    change_type: ChangeType
    attributes_added: List[AttributeChange]
    attributes_changed: List[AttributeChange]
    attributes_deleted: List[AttributeChange]
    nested_changes: List[Dict[str, Any]]
    has_sensitive: bool
    has_computed: bool


@dataclass
class OutputChange:
    name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    is_sensitive: bool = False


@dataclass
class PlanSummary:
    to_add: int
    to_change: int
    to_destroy: int
    resource_changes: List[ResourceChange]
    output_changes: List[OutputChange]
    has_changes: bool
    has_errors: bool
    error_messages: List[str]
    raw_plan: str


class TerraformPlanParser:
    """Parser for Terraform plan output."""
    
    def __init__(self):
        # Regex patterns for parsing
        self.change_header_pattern = re.compile(
            r'^  # (.+?) will be (.+?)$'
        )
        self.resource_address_pattern = re.compile(
            r'^(.+?)\.(.+?)(?:\[(.+?)\])?$'
        )
        self.summary_pattern = re.compile(
            r'Plan: (\d+) to add, (\d+) to change, (\d+) to destroy'
        )
        self.no_changes_pattern = re.compile(
            r'No changes\. Infrastructure is up-to-date\.'
        )
        self.attribute_change_pattern = re.compile(
            r'^  ([~+-])\s*(.+?)\s*=\s*(.+?)(?:\s*->\s*(.+?))?$'
        )
        
        # Error detection patterns
        self.error_patterns = [
            # Generic error patterns
            re.compile(r'^Error:', re.IGNORECASE | re.MULTILINE),
            re.compile(r'Error [a-zA-Z]+:', re.IGNORECASE),
            re.compile(r'╷\s*│\s*Error:', re.MULTILINE),
            
            # Authentication and permission errors
            re.compile(r'(AccessDenied|Access Denied|Forbidden|Unauthorized)', re.IGNORECASE),
            re.compile(r'No valid credential sources found', re.IGNORECASE),
            re.compile(r'Unable to locate credentials', re.IGNORECASE),
            re.compile(r'authentication failed', re.IGNORECASE),
            re.compile(r'Invalid credentials', re.IGNORECASE),
            
            # Configuration and syntax errors
            re.compile(r'Invalid (character|expression|resource|reference|argument)', re.IGNORECASE),
            re.compile(r'Missing required argument', re.IGNORECASE),
            re.compile(r'Unsupported argument', re.IGNORECASE),
            re.compile(r'Configuration .* is not valid', re.IGNORECASE),
            re.compile(r'Syntax error', re.IGNORECASE),
            
            # Provider and resource errors
            re.compile(r'Provider .* doesn\'t support', re.IGNORECASE),
            re.compile(r'Failed to (configure|install|download) provider', re.IGNORECASE),
            re.compile(r'Resource not found', re.IGNORECASE),
            re.compile(r'(InvalidAMIID|InvalidInstanceType|InvalidSubnet)', re.IGNORECASE),
            re.compile(r'(BucketAlreadyExists|BucketNotEmpty)', re.IGNORECASE),
            
            # State and locking errors
            re.compile(r'Error (acquiring|locking) .* state', re.IGNORECASE),
            re.compile(r'State lock', re.IGNORECASE),
            re.compile(r'Backend configuration', re.IGNORECASE),
            
            # Cycle and dependency errors
            re.compile(r'Cycle:', re.IGNORECASE),
            re.compile(r'Dependency cycle', re.IGNORECASE),
            
            # Template and data source errors
            re.compile(r'Error rendering template', re.IGNORECASE),
            re.compile(r'Invalid data source', re.IGNORECASE),
            
            # Network and infrastructure errors
            re.compile(r'(InvalidSubnet\.Range|InvalidVpcID|InvalidRouteTableID)', re.IGNORECASE),
            re.compile(r'Network .* error', re.IGNORECASE),
            
            # API and service errors
            re.compile(r'API Error', re.IGNORECASE),
            re.compile(r'Service .* (unavailable|error)', re.IGNORECASE),
            re.compile(r'Request failed', re.IGNORECASE),
            
            # Generic failure patterns
            re.compile(r'Failed to .+', re.IGNORECASE),
            re.compile(r'Could not .+', re.IGNORECASE),
            re.compile(r'Unable to .+', re.IGNORECASE),
            
            # Terraform-specific error markers
            re.compile(r'Terraform encountered an error', re.IGNORECASE),
            re.compile(r'Planning failed', re.IGNORECASE),
            re.compile(r'Operation failed', re.IGNORECASE),
        ]
        
    def _detect_errors(self, plan_text: str) -> Tuple[bool, List[str]]:
        """Detect if the plan text contains errors or is empty/invalid."""
        error_messages = []
        has_errors = False
        
        # Check for empty or nearly empty input
        stripped_text = plan_text.strip()
        if not stripped_text:
            has_errors = True
            error_messages.append("Empty terraform plan output")
            return has_errors, error_messages
        
        # Check for very minimal content (less than 50 characters likely means something went wrong)
        if len(stripped_text) < 50:
            has_errors = True
            error_messages.append("Terraform plan output too short - possibly failed")
            return has_errors, error_messages
        
        lines = [line.strip() for line in plan_text.split('\n') if line.strip()]
        
        # Check for insufficient content (fewer than 3 meaningful lines suggests failure)
        if len(lines) < 3:
            has_errors = True
            error_messages.append("Insufficient terraform plan content")
            return has_errors, error_messages
        
        # Check if this looks like a valid terraform plan by looking for expected patterns
        has_terraform_indicators = any([
            'terraform' in plan_text.lower(),
            'plan:' in plan_text.lower(),
            'no changes' in plan_text.lower(),
            'will be created' in plan_text,
            'will be destroyed' in plan_text,
            'will be updated' in plan_text,
            'will be replaced' in plan_text,
            'execution plan' in plan_text.lower(),
        ])
        
        if not has_terraform_indicators:
            has_errors = True
            error_messages.append("Input does not appear to be valid terraform plan output")
            return has_errors, error_messages
        
        # Check for explicit error patterns (keeping some of the original logic for actual error messages)
        for pattern in self.error_patterns:
            matches = pattern.findall(plan_text)
            if matches:
                has_errors = True
                # Find the lines containing errors for context
                for line in lines:
                    if pattern.search(line):
                        error_messages.append(line.strip())
        
        # Check for specific terraform error indicators
        if any('terraform init' in line.lower() and 'required' in line.lower() for line in lines):
            has_errors = True
            error_messages.append("Terraform initialization required")
        
        # Check for exit status indicators that suggest errors
        if any(line.strip().startswith('Error:') for line in lines):
            has_errors = True
        
        # Look for terraform's box-drawing error format
        if '╷' in plan_text and '│' in plan_text and 'Error:' in plan_text:
            has_errors = True
            # Extract the error message from the box format
            in_error_box = False
            for line in lines:
                if '╷' in line:
                    in_error_box = True
                elif '╵' in line:
                    in_error_box = False
                elif in_error_box and '│' in line:
                    error_msg = line.replace('│', '').strip()
                    if error_msg and error_msg not in error_messages:
                        error_messages.append(error_msg)
        
        # If no errors found so far, but we have a very short plan that doesn't match expected patterns
        if not has_errors and len(stripped_text) < 200:
            # Check if it's just a simple "no changes" message
            if not (self.no_changes_pattern.search(plan_text) or 
                   'no changes' in plan_text.lower() or
                   'up-to-date' in plan_text.lower()):
                has_errors = True
                error_messages.append("Terraform plan output appears incomplete or invalid")
        
        # Remove duplicates while preserving order
        unique_errors = []
        for msg in error_messages:
            if msg and msg not in unique_errors:
                unique_errors.append(msg)
        
        return has_errors, unique_errors[:10]  # Limit to first 10 error messages
        
    def parse(self, plan_text: str) -> PlanSummary:
        """Parse terraform plan text into structured data."""
        # First check for errors
        has_errors, error_messages = self._detect_errors(plan_text)
        
        # If errors are detected, return early with error information
        if has_errors:
            return PlanSummary(
                to_add=0,
                to_change=0,
                to_destroy=0,
                resource_changes=[],
                output_changes=[],
                has_changes=False,
                has_errors=True,
                error_messages=error_messages,
                raw_plan=plan_text
            )
        
        lines = plan_text.split('\n')
        
        # Check for no changes
        if any(self.no_changes_pattern.search(line) for line in lines):
            return PlanSummary(
                to_add=0,
                to_change=0,
                to_destroy=0,
                resource_changes=[],
                output_changes=[],
                has_changes=False,
                has_errors=False,
                error_messages=[],
                raw_plan=plan_text
            )
        
        resource_changes = []
        output_changes = []
        to_add = to_change = to_destroy = 0
        
        i = 0
        while i < len(lines):
            line = lines[i].rstrip()
            
            # Check for change header
            header_match = self.change_header_pattern.match(line)
            if header_match:
                resource_address = header_match.group(1)
                action = header_match.group(2)
                
                # Parse the resource change block
                resource_change, end_index = self._parse_resource_change(
                    lines, i, resource_address, action
                )
                if resource_change:
                    resource_changes.append(resource_change)
                    
                    # Update counters
                    if resource_change.change_type == ChangeType.CREATE:
                        to_add += 1
                    elif resource_change.change_type == ChangeType.UPDATE:
                        to_change += 1
                    elif resource_change.change_type == ChangeType.DELETE:
                        to_destroy += 1
                    elif resource_change.change_type == ChangeType.REPLACE:
                        to_add += 1
                        to_destroy += 1
                
                i = end_index
            else:
                # Check for summary line
                summary_match = self.summary_pattern.search(line)
                if summary_match:
                    to_add = int(summary_match.group(1))
                    to_change = int(summary_match.group(2))
                    to_destroy = int(summary_match.group(3))
                
                # Check for output changes
                if line.strip().startswith('Outputs:'):
                    output_changes = self._parse_output_changes(lines, i)
                
                i += 1
        
        return PlanSummary(
            to_add=to_add,
            to_change=to_change,
            to_destroy=to_destroy,
            resource_changes=resource_changes,
            output_changes=output_changes,
            has_changes=len(resource_changes) > 0 or len(output_changes) > 0,
            has_errors=False,
            error_messages=[],
            raw_plan=plan_text
        )
    
    def _parse_resource_change(self, lines: List[str], start_index: int, 
                             resource_address: str, action: str) -> Tuple[Optional[ResourceChange], int]:
        """Parse a single resource change block."""
        # Determine change type
        change_type = self._parse_change_type(action)
        
        # Parse resource type and name
        resource_type, resource_name = self._parse_resource_address(resource_address)
        
        # Parse attributes
        attributes_added = []
        attributes_changed = []
        attributes_deleted = []
        nested_changes = []
        has_sensitive = False
        has_computed = False
        
        i = start_index + 1
        while i < len(lines) and not lines[i].strip().startswith('#'):
            line = lines[i].rstrip()
            
            if not line.strip():
                i += 1
                continue
            
            # Check if this is the start of a new resource block
            if self.change_header_pattern.match(line):
                break
            
            # Parse attribute changes
            attr_match = self.attribute_change_pattern.match(line)
            if attr_match:
                change_op = attr_match.group(1)
                attr_name = attr_match.group(2)
                old_value = attr_match.group(3) if len(attr_match.groups()) >= 3 else None
                new_value = attr_match.group(4) if len(attr_match.groups()) >= 4 else None
                
                # Check for sensitive/computed values
                is_sensitive = "(sensitive value)" in line
                is_computed = "<computed>" in line or "(known after apply)" in line
                
                if is_sensitive:
                    has_sensitive = True
                if is_computed:
                    has_computed = True
                
                attr_change = AttributeChange(
                    name=attr_name,
                    old_value=old_value,
                    new_value=new_value,
                    is_sensitive=is_sensitive,
                    is_computed=is_computed
                )
                
                if change_op == '+':
                    attributes_added.append(attr_change)
                elif change_op == '-':
                    attributes_deleted.append(attr_change)
                elif change_op == '~':
                    attributes_changed.append(attr_change)
            
            i += 1
        
        resource_change = ResourceChange(
            resource_address=resource_address,
            resource_type=resource_type,
            resource_name=resource_name,
            change_type=change_type,
            attributes_added=attributes_added,
            attributes_changed=attributes_changed,
            attributes_deleted=attributes_deleted,
            nested_changes=nested_changes,
            has_sensitive=has_sensitive,
            has_computed=has_computed
        )
        
        return resource_change, i
    
    def _parse_change_type(self, action: str) -> ChangeType:
        """Parse the action string to determine change type."""
        action_lower = action.lower()
        if "created" in action_lower:
            return ChangeType.CREATE
        elif "updated" in action_lower or "modified" in action_lower:
            return ChangeType.UPDATE
        elif "destroyed" in action_lower:
            return ChangeType.DELETE
        elif "replaced" in action_lower:
            return ChangeType.REPLACE
        else:
            return ChangeType.NO_OP
    
    def _parse_resource_address(self, address: str) -> Tuple[str, str]:
        """Parse resource address to extract type and name."""
        original_address = address
        
        # Handle indexed resources by removing just the index brackets, not the content after
        # Transform: module.a[0].aws_instance.example[1] -> module.a.aws_instance.example
        import re
        address = re.sub(r'\[\d+\]', '', address)
        
        # For module resources, extract the actual resource type and name
        if address.startswith('module.'):
            parts = address.split('.')
            
            # Look for the actual resource type (like aws_autoscaling_group, aws_launch_template)
            # These typically start with a provider prefix (aws_, google_, azurerm_, etc.)
            for i in range(len(parts)):
                part = parts[i]
                # Check if this looks like a resource type (provider_resourcetype pattern)
                if ('_' in part and 
                    not part.startswith('module') and 
                    i < len(parts) - 1):  # Must have a name after it
                    resource_type = part
                    resource_name = parts[i + 1]
                    return resource_type, resource_name
            
            # Fallback: if no standard resource type found, use the last two parts
            if len(parts) >= 2:
                return parts[-2], parts[-1]
            else:
                return parts[-1], ""
        
        # Regular resource (not in module)
        if '.' in address:
            resource_type, resource_name = address.split('.', 1)
        else:
            resource_type = address
            resource_name = ""
        
        return resource_type, resource_name
    
    def _parse_output_changes(self, lines: List[str], start_index: int) -> List[OutputChange]:
        """Parse output changes section."""
        output_changes = []
        i = start_index + 1
        
        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith('─'):
                i += 1
                continue
            
            # Look for output definitions
            if '=' in line:
                parts = line.split('=', 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    value = parts[1].strip()
                    is_sensitive = "(sensitive value)" in value
                    
                    output_changes.append(OutputChange(
                        name=name,
                        new_value=value if not is_sensitive else "(sensitive)",
                        is_sensitive=is_sensitive
                    ))
            
            i += 1
        
        return output_changes
    
    def to_json(self, plan_summary: PlanSummary) -> str:
        """Convert plan summary to JSON."""
        def convert_dataclass(obj):
            if hasattr(obj, '__dict__'):
                result = {}
                for key, value in obj.__dict__.items():
                    if isinstance(value, Enum):
                        result[key] = value.value
                    elif isinstance(value, list):
                        result[key] = [convert_dataclass(item) for item in value]
                    elif hasattr(value, '__dict__'):
                        result[key] = convert_dataclass(value)
                    else:
                        result[key] = value
                return result
            return obj
        
        return json.dumps(convert_dataclass(plan_summary), indent=2)
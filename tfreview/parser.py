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
        
    def parse(self, plan_text: str) -> PlanSummary:
        """Parse terraform plan text into structured data."""
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
        # Remove module prefix if present
        if address.startswith('module.'):
            parts = address.split('.')
            # Find the actual resource part (not module parts)
            for i, part in enumerate(parts):
                if not part.startswith('module') and '.' in '.'.join(parts[i:]):
                    address = '.'.join(parts[i:])
                    break
        
        # Handle indexed resources
        if '[' in address:
            address = address.split('[')[0]
        
        # Split into type and name
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
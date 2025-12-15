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
    MOVED = "moved"
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
    was_moved_from: Optional[str] = None  # Track if this resource was moved from another address


@dataclass
class OutputChange:
    name: str
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    is_sensitive: bool = False


@dataclass
class TerraformError:
    title: str
    message: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    is_warning: bool = False


@dataclass
class PlanSummary:
    to_add: int
    to_change: int
    to_destroy: int
    to_replace: int
    resource_changes: List[ResourceChange]
    output_changes: List[OutputChange]
    has_changes: bool
    raw_plan: str
    errors: List[TerraformError]
    warnings: List[TerraformError]
    has_errors: bool
    has_warnings: bool


class TerraformPlanParser:
    """Parser for Terraform plan output."""

    def __init__(self):
        # Regex patterns for parsing
        self.change_header_pattern = re.compile(
            r"^  # (.+?) will be (.+?)$|^  # (.+?) must be (.+?)$"
        )
        # Pattern for "has moved to" changes
        self.moved_pattern = re.compile(
            r"^  # (.+?) has moved to (.+?)$"
        )
        self.resource_address_pattern = re.compile(r"^(.+?)\.(.+?)(?:\[(.+?)\])?$")
        self.summary_pattern = re.compile(
            r"Plan: (\d+) to add, (\d+) to change, (\d+) to destroy"
        )
        self.no_changes_pattern = re.compile(
            r"No changes\. Infrastructure is up-to-date\."
        )
        self.attribute_change_pattern = re.compile(
            r"^  ([~+-])\s*(.+?)\s*=\s*(.+?)(?:\s*->\s*(.+?))?$"
        )
        # Add pattern for replacement indicators
        self.replacement_pattern = re.compile(
            r"^  ([+-]/[+-])\s*(.+?)\s*=\s*(.+?)(?:\s*->\s*(.+?))?$"
        )

        # Pattern for error blocks (╷ starts error, ╵ ends error)
        self.error_start_pattern = re.compile(r"^╷\s*$")
        self.error_end_pattern = re.compile(r"^╵\s*$")

    def parse(self, plan_text: str) -> PlanSummary:
        """Parse terraform plan text into structured data."""
        lines = plan_text.split("\n")

        # Parse errors first
        errors, warnings = self._parse_errors(lines)

        # Check for no changes
        if any(self.no_changes_pattern.search(line) for line in lines):
            return PlanSummary(
                to_add=0,
                to_change=0,
                to_destroy=0,
                to_replace=0,
                resource_changes=[],
                output_changes=[],
                has_changes=False,
                raw_plan=plan_text,
                errors=errors,
                warnings=warnings,
                has_errors=len(errors) > 0,
                has_warnings=len(warnings) > 0,
            )

        resource_changes = []
        output_changes = []
        to_add = to_change = to_destroy = to_replace = 0

        i = 0
        while i < len(lines):
            line = lines[i].rstrip()

            # Check for change header
            header_match = self.change_header_pattern.match(line)
            moved_match = self.moved_pattern.match(line)

            if header_match:
                # Handle both "will be" and "must be" patterns
                if header_match.group(1) and header_match.group(2):
                    # "will be" pattern
                    resource_address = header_match.group(1)
                    action = header_match.group(2)
                elif header_match.group(3) and header_match.group(4):
                    # "must be" pattern
                    resource_address = header_match.group(3)
                    action = header_match.group(4)
                else:
                    i += 1
                    continue

                # Parse the resource change block
                resource_change, end_index = self._parse_resource_change(
                    lines, i, resource_address, action
                )
                if resource_change:
                    resource_changes.append(resource_change)

                    # If this resource was moved from somewhere else, create a duplicate with MOVED type
                    if resource_change.was_moved_from:
                        moved_resource = ResourceChange(
                            resource_address=resource_change.resource_address,
                            resource_type=resource_change.resource_type,
                            resource_name=resource_change.resource_name,
                            change_type=ChangeType.MOVED,
                            attributes_added=[],
                            attributes_changed=[],
                            attributes_deleted=[],
                            nested_changes=[],
                            has_sensitive=False,
                            has_computed=False,
                            was_moved_from=resource_change.was_moved_from,
                        )
                        resource_changes.append(moved_resource)

                    # Update counters
                    if resource_change.change_type == ChangeType.CREATE:
                        to_add += 1
                    elif resource_change.change_type == ChangeType.UPDATE:
                        to_change += 1
                    elif resource_change.change_type == ChangeType.DELETE:
                        to_destroy += 1
                    elif resource_change.change_type == ChangeType.REPLACE:
                        to_replace += 1

                i = end_index
            elif moved_match:
                # Handle "has moved to" pattern
                old_address = moved_match.group(1)
                new_address = moved_match.group(2)

                # Parse the resource change block for moved resources
                resource_change, end_index = self._parse_moved_resource(
                    lines, i, old_address, new_address
                )
                if resource_change:
                    resource_changes.append(resource_change)
                    # Moved resources don't count towards any of the action counters

                i = end_index
            else:
                # Check for summary line
                summary_match = self.summary_pattern.search(line)
                if summary_match:
                    # Do not overwrite our own counters with the summary line
                    pass

                # Check for output changes
                if line.strip().startswith("Outputs:"):
                    output_changes = self._parse_output_changes(lines, i)

                i += 1

        return PlanSummary(
            to_add=to_add,
            to_change=to_change,
            to_destroy=to_destroy,
            to_replace=to_replace,
            resource_changes=resource_changes,
            output_changes=output_changes,
            has_changes=len(resource_changes) > 0 or len(output_changes) > 0,
            raw_plan=plan_text,
            errors=errors,
            warnings=warnings,
            has_errors=len(errors) > 0,
            has_warnings=len(warnings) > 0,
        )

    def _parse_resource_change(
        self, lines: List[str], start_index: int, resource_address: str, action: str
    ) -> Tuple[Optional[ResourceChange], int]:
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
        was_moved_from = None

        i = start_index + 1
        while i < len(lines):
            line = lines[i].rstrip()

            # Check for delimiter: blank line followed by "  #" (next resource) or "Plan:" (summary)
            if not line.strip() and i + 1 < len(lines):
                next_line = lines[i + 1]
                if next_line.startswith("  #") or next_line.startswith("Plan:"):
                    break

            if not line.strip():
                i += 1
                continue

            # Check for "(moved from" pattern
            if "(moved from " in line:
                # Extract the original address from the line
                import re
                moved_from_match = re.search(r'\(moved from (.+?)\)', line)
                if moved_from_match:
                    was_moved_from = moved_from_match.group(1)

            # Parse attribute changes
            attr_match = self.attribute_change_pattern.match(line)
            replacement_match = self.replacement_pattern.match(line)

            if attr_match:
                change_op = attr_match.group(1)
                attr_name = attr_match.group(2)
                old_value = (
                    attr_match.group(3) if len(attr_match.groups()) >= 3 else None
                )
                new_value = (
                    attr_match.group(4) if len(attr_match.groups()) >= 4 else None
                )

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
                    is_computed=is_computed,
                )

                if change_op == "+":
                    attributes_added.append(attr_change)
                elif change_op == "-":
                    attributes_deleted.append(attr_change)
                elif change_op == "~":
                    attributes_changed.append(attr_change)
            elif replacement_match:
                # Handle replacement pattern (-/+ or +/-)
                change_op = replacement_match.group(1)
                attr_name = replacement_match.group(2)
                old_value = (
                    replacement_match.group(3)
                    if len(replacement_match.groups()) >= 3
                    else None
                )
                new_value = (
                    replacement_match.group(4)
                    if len(replacement_match.groups()) >= 4
                    else None
                )

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
                    is_computed=is_computed,
                )

                # For replacements, we add to both deleted and added
                attributes_deleted.append(attr_change)
                attributes_added.append(attr_change)

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
            has_computed=has_computed,
            was_moved_from=was_moved_from,
        )

        return resource_change, i

    def _parse_moved_resource(
        self, lines: List[str], start_index: int, old_address: str, new_address: str
    ) -> Tuple[Optional[ResourceChange], int]:
        """Parse a moved resource block."""
        # Use the new address as the primary address
        resource_type, resource_name = self._parse_resource_address(new_address)

        # For moved resources, we don't typically have attribute changes
        attributes_added = []
        attributes_changed = []
        attributes_deleted = []
        nested_changes = []
        has_sensitive = False
        has_computed = False

        # Move to the next line after the header
        i = start_index + 1

        # Skip through the resource block (moved resources typically show the resource definition)
        while i < len(lines):
            line = lines[i].rstrip()

            # Check for delimiter: blank line followed by "  #" (next resource) or "Plan:" (summary)
            if not line.strip() and i + 1 < len(lines):
                next_line = lines[i + 1]
                if next_line.startswith("  #") or next_line.startswith("Plan:"):
                    break

            if not line.strip():
                i += 1
                continue

            # For moved resources, just skip through the resource definition block
            # We could parse attributes here if needed, but typically they're unchanged
            i += 1

        resource_change = ResourceChange(
            resource_address=new_address,  # Use the new address
            resource_type=resource_type,
            resource_name=resource_name,
            change_type=ChangeType.MOVED,
            attributes_added=attributes_added,
            attributes_changed=attributes_changed,
            attributes_deleted=attributes_deleted,
            nested_changes=nested_changes,
            has_sensitive=has_sensitive,
            has_computed=has_computed,
            was_moved_from=old_address,
        )

        return resource_change, i

    def _parse_change_type(self, action: str) -> ChangeType:
        """Parse the action string to determine change type."""
        action_lower = action.lower()
        if "created" in action_lower or "create" in action_lower:
            return ChangeType.CREATE
        elif (
            "updated" in action_lower
            or "modified" in action_lower
            or "update" in action_lower
        ):
            return ChangeType.UPDATE
        elif "destroyed" in action_lower or "destroy" in action_lower:
            return ChangeType.DELETE
        elif "replaced" in action_lower or "replace" in action_lower:
            return ChangeType.REPLACE
        else:
            return ChangeType.NO_OP

    def _parse_resource_address(self, address: str) -> Tuple[str, str]:
        """Parse resource address to extract type and name."""
        original_address = address

        # Handle indexed resources by removing just the index brackets, not the content after
        # Transform: module.a[0].aws_instance.example[1] -> module.a.aws_instance.example
        import re

        address = re.sub(r"\[\d+\]", "", address)

        # For module resources, extract the actual resource type and name
        if address.startswith("module."):
            parts = address.split(".")

            # Look for the actual resource type (like aws_autoscaling_group, aws_launch_template)
            # These typically start with a provider prefix (aws_, google_, azurerm_, etc.)
            for i in range(len(parts)):
                part = parts[i]
                # Check if this looks like a resource type (provider_resourcetype pattern)
                if (
                    "_" in part and not part.startswith("module") and i < len(parts) - 1
                ):  # Must have a name after it
                    resource_type = part
                    resource_name = parts[i + 1]
                    return resource_type, resource_name

            # Fallback: if no standard resource type found, use the last two parts
            if len(parts) >= 2:
                return parts[-2], parts[-1]
            else:
                return parts[-1], ""

        # Regular resource (not in module)
        if "." in address:
            resource_type, resource_name = address.split(".", 1)
        else:
            resource_type = address
            resource_name = ""

        return resource_type, resource_name

    def _parse_output_changes(
        self, lines: List[str], start_index: int
    ) -> List[OutputChange]:
        """Parse output changes section."""
        output_changes = []
        i = start_index + 1

        while i < len(lines):
            line = lines[i].strip()
            if not line or line.startswith("─"):
                i += 1
                continue

            # Look for output definitions
            if "=" in line:
                parts = line.split("=", 1)
                if len(parts) == 2:
                    name = parts[0].strip()
                    value = parts[1].strip()
                    is_sensitive = "(sensitive value)" in value

                    output_changes.append(
                        OutputChange(
                            name=name,
                            new_value=value if not is_sensitive else "(sensitive)",
                            is_sensitive=is_sensitive,
                        )
                    )

            i += 1

        return output_changes

    def _parse_errors(self, lines: List[str]) -> Tuple[List[TerraformError], List[TerraformError]]:
        """Parse diagnostic blocks (errors and warnings) from terraform plan output."""
        errors: List[TerraformError] = []
        warnings: List[TerraformError] = []
        i = 0

        while i < len(lines):
            line = lines[i].rstrip()

            # Check for error block start
            if self.error_start_pattern.match(line):
                diagnostic, end_index = self._parse_single_error(lines, i)
                if diagnostic:
                    if diagnostic.is_warning:
                        warnings.append(diagnostic)
                    else:
                        errors.append(diagnostic)
                i = end_index
            else:
                i += 1

        return errors, warnings

    def _parse_single_error(self, lines: List[str], start_index: int) -> Tuple[Optional[TerraformError], int]:
        """Parse a single error block starting with ╷ and ending with ╵."""
        i = start_index + 1
        error_lines: List[str] = []
        title = ""
        file_path: Optional[str] = None
        line_number: Optional[int] = None
        is_warning = False

        while i < len(lines):
            line = lines[i].rstrip()

            # Check for error block end
            if self.error_end_pattern.match(line):
                break

            # Skip empty lines at the start
            if not line.strip() and not error_lines:
                i += 1
                continue

            error_lines.append(line)
            i += 1

        if not error_lines:
            return None, i + 1

        # Extract title (first non-empty line starting with │)
        for line in error_lines:
            clean_line = line.lstrip("│ ").strip()
            if clean_line.startswith("Error:"):
                # For very long error messages, truncate the title but keep full message
                if len(clean_line) > 300:
                    # Extract first part: "Error: " + first 250 chars of message
                    title = clean_line[:300] + "..."
                else:
                    title = clean_line
                is_warning = False
                break
            elif clean_line.startswith("Warning:"):
                if len(clean_line) > 300:
                    title = clean_line[:300] + "..."
                else:
                    title = clean_line
                is_warning = True
                break

        # Look for file path and line number
        for line in error_lines:
            # Pattern: "│   on path/to/file.tf line 12, in resource..."
            if "on " in line and " line " in line:
                parts = line.split()
                try:
                    on_idx = parts.index("on")
                    line_idx = parts.index("line")
                    if on_idx < len(parts) - 1 and line_idx < len(parts) - 1:
                        file_path = parts[on_idx + 1].rstrip(",")
                        line_number = int(parts[line_idx + 1].rstrip(","))
                except (ValueError, IndexError):
                    pass
                break

        # Build the full error message from all lines
        message_lines = []
        for line in error_lines:
            # Clean up the box drawing characters
            clean_line = line.lstrip("│ ").rstrip()
            if clean_line:
                message_lines.append(clean_line)

        message = "\n".join(message_lines)

        if not title:
            title = "Terraform Warning" if is_warning else "Terraform Error"

        return TerraformError(
            title=title,
            message=message,
            file_path=file_path,
            line_number=line_number,
            is_warning=is_warning,
        ), i + 1

"""
HTML Renderer for Terraform Plan Review Interface.
"""

import os
import re
from pathlib import Path
from typing import Dict, Any, Optional, Union
from jinja2 import Template, Environment, FileSystemLoader
from .parser import PlanSummary, ChangeType, ResourceChange


class HTMLRenderer:
    """Renders terraform plan data as HTML with interactive review interface."""
    
    def __init__(self, templates_dir: Optional[Union[str, Path]] = None):
        """Initialize the HTML renderer."""
        if templates_dir is None:
            # Default to templates directory relative to this file
            templates_dir = Path(__file__).parent.parent / "templates"
        
        self.templates_dir = Path(templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=True
        )
        
        # Register custom filters
        self.env.filters['colorize_terraform'] = self._colorize_terraform_output
        self.env.filters['change_type_class'] = self._get_change_type_class
        self.env.filters['change_type_icon'] = self._get_change_type_icon
        self.env.filters['extract_resource_diff'] = self._extract_resource_diff
        self.env.filters['escapejs'] = self._escape_js
    
    def render(self, plan_summary: PlanSummary, output_file: Optional[str] = None) -> str:
        """Render the plan summary as HTML."""
        template = self.env.get_template('plan_review.html')
        
        html_content = template.render(
            plan=plan_summary,
            change_types=ChangeType,
            enumerate=enumerate
        )
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
        
        return html_content
    
    def _colorize_terraform_output(self, text: str) -> str:
        """Add HTML styling to terraform output for syntax highlighting."""
        if not text:
            return text
        
        # Escape HTML first
        text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        # Color coding for different types of changes
        patterns = [
            (r'^(\s*\+\s)', r'<span class="tf-add">\1</span>'),
            (r'^(\s*-\s)', r'<span class="tf-delete">\1</span>'),
            (r'^(\s*~\s)', r'<span class="tf-change">\1</span>'),
            (r'^(\s*-/\+\s)', r'<span class="tf-replace">\1</span>'),
            (r'\(sensitive value\)', r'<span class="tf-sensitive">(sensitive value)</span>'),
            (r'\(known after apply\)', r'<span class="tf-computed">(known after apply)</span>'),
            (r'&lt;computed&gt;', r'<span class="tf-computed">&lt;computed&gt;</span>'),
        ]
        
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
        
        return text
    
    def _get_change_type_class(self, change_type: ChangeType) -> str:
        """Get CSS class for change type."""
        class_map = {
            ChangeType.CREATE: "change-create",
            ChangeType.UPDATE: "change-update", 
            ChangeType.DELETE: "change-delete",
            ChangeType.REPLACE: "change-replace",
            ChangeType.NO_OP: "change-noop"
        }
        return class_map.get(change_type, "change-unknown")
    
    def _get_change_type_icon(self, change_type: ChangeType) -> str:
        """Get icon for change type."""
        icon_map = {
            ChangeType.CREATE: "➕",
            ChangeType.UPDATE: "🔄",
            ChangeType.DELETE: "❌",
            ChangeType.REPLACE: "🔄",
            ChangeType.NO_OP: "⚪"
        }
        return icon_map.get(change_type, "❓")
    
    def _extract_resource_diff(self, raw_plan: str, resource_change: ResourceChange) -> str:
        """Extract the raw diff for a specific resource from the plan."""
        lines = raw_plan.split('\n')
        diff_lines = []
        found_resource = False
        
        for line in lines:
            if resource_change.resource_address in line and "will be" in line:
                found_resource = True
                diff_lines.append(line)
                continue
            
            if found_resource:
                # Stop if we hit another resource
                if line.strip().startswith('#') and "will be" in line:
                    break
                
                # Add lines that are part of this resource's diff
                if line.strip() and (line.startswith('  +') or line.startswith('  -') or 
                                   line.startswith('  ~') or line.startswith('    ')):
                    diff_lines.append(line)
                elif not line.strip():
                    diff_lines.append(line)
                else:
                    # If we hit a non-empty line that's not part of the diff, we're done
                    if line.strip() and not line.startswith('  '):
                        break
        
        return '\n'.join(diff_lines)
    
    def create_standalone_html(self, plan_summary: PlanSummary) -> str:
        """Create a standalone HTML file with embedded CSS and JavaScript."""
        template = self.env.get_template('standalone.html')
        
        return template.render(
            plan=plan_summary,
            change_types=ChangeType,
            enumerate=enumerate
        )
    
    def _get_css_content(self) -> str:
        """Get CSS content for standalone HTML."""
        css_file = self.templates_dir / "styles.css"
        if css_file.exists():
            return css_file.read_text(encoding='utf-8')
        return ""
    
    def _get_js_content(self) -> str:
        """Get JavaScript content for standalone HTML."""
        js_file = self.templates_dir / "script.js"
        if js_file.exists():
            return js_file.read_text(encoding='utf-8')
        return ""

    def _escape_js(self, text: str) -> str:
        """Escape JavaScript content for HTML."""
        return (text.replace('\\', '\\\\')
                   .replace('\n', '\\n')
                   .replace('\r', '\\r')
                   .replace('\t', '\\t')
                   .replace('"', '\\"')
                   .replace("'", "\\'")
                   .replace('`', '\\`')
                   .replace('</', '<\\/'))
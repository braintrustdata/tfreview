"""
Test cases for HTML Renderer.
"""

import pytest
from pathlib import Path
from tfreview.parser import TerraformPlanParser
from tfreview.renderer import HTMLRenderer


class TestHTMLRenderer:
    """Test cases for the HTML renderer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = TerraformPlanParser()
        self.renderer = HTMLRenderer()
        self.samples_dir = Path(__file__).parent.parent / "samples"

    def load_sample(self, filename: str) -> str:
        """Load a sample plan file."""
        return (self.samples_dir / filename).read_text(encoding="utf-8")

    def test_renderer_initialization(self):
        """Test renderer initialization."""
        assert self.renderer is not None
        assert self.renderer.templates_dir.exists()
        assert self.renderer.env is not None

    def test_colorize_terraform_output(self):
        """Test terraform output colorization."""
        test_cases = [
            ("  + create", '<span class="tf-add">  + </span>create'),
            ("  - destroy", '<span class="tf-delete">  - </span>destroy'),
            ("  ~ update", '<span class="tf-change">  ~ </span>update'),
            ("  -/+ replace", '<span class="tf-replace">  -/+ </span>replace'),
            (
                "(sensitive value)",
                '<span class="tf-sensitive">(sensitive value)</span>',
            ),
            (
                "(known after apply)",
                '<span class="tf-computed">(known after apply)</span>',
            ),
        ]

        for input_text, expected in test_cases:
            result = self.renderer._colorize_terraform_output(input_text)
            assert expected in result

    def test_forces_replacement_highlighting(self):
        """Test that '# forces replacement' is highlighted in resource diffs but not in full plan."""
        test_text = '  ~ instance_type = "t3.micro" -> "t3.small" # forces replacement'

        # Test resource diff highlighting (should include forces replacement)
        result_diff = self.renderer._colorize_terraform_output(test_text)
        assert (
            '<span class="tf-forces-replacement"># forces replacement</span>'
            in result_diff
        )

        # Test full plan highlighting (should not include forces replacement)
        result_full = self.renderer._colorize_terraform_output_full(test_text)
        assert (
            '<span class="tf-forces-replacement"># forces replacement</span>'
            not in result_full
        )
        # But should still include other highlighting
        assert '<span class="tf-change">  ~ </span>' in result_full

    def test_change_type_class_mapping(self):
        """Test CSS class mapping for change types."""
        from tfreview.parser import ChangeType

        test_cases = [
            (ChangeType.CREATE, "change-create"),
            (ChangeType.UPDATE, "change-update"),
            (ChangeType.DELETE, "change-delete"),
            (ChangeType.REPLACE, "change-replace"),
            (ChangeType.NO_OP, "change-noop"),
        ]

        for change_type, expected_class in test_cases:
            result = self.renderer._get_change_type_class(change_type)
            assert result == expected_class

    def test_change_type_icon_mapping(self):
        """Test icon mapping for change types."""
        from tfreview.parser import ChangeType

        test_cases = [
            (ChangeType.CREATE, "➕"),
            (ChangeType.UPDATE, "✏️"),
            (ChangeType.DELETE, "❌"),
            (ChangeType.REPLACE, "🔄"),
            (ChangeType.NO_OP, "⚪"),
        ]

        for change_type, expected_icon in test_cases:
            result = self.renderer._get_change_type_icon(change_type)
            assert result == expected_icon

    def test_create_standalone_html(self):
        """Test creation of standalone HTML."""
        # Parse a sample plan
        plan_text = self.load_sample("sample_plan_1.txt")
        plan_summary = self.parser.parse(plan_text)

        # Generate HTML
        html_content = self.renderer.create_standalone_html(plan_summary)

        # Basic HTML structure checks
        assert "<!DOCTYPE html>" in html_content
        assert "<html" in html_content
        assert "<head>" in html_content
        assert "<body>" in html_content
        assert "Terraform Plan Review" in html_content

        # Check for plan summary info
        assert "1 to add" in html_content
        assert "1 to change" in html_content
        assert "1 to destroy" in html_content

        # Check for resource cards
        assert "aws_instance.example" in html_content
        assert "aws_security_group.web" in html_content
        assert "aws_s3_bucket.legacy" in html_content

        # Check for interactive elements
        assert "toggleResource" in html_content
        assert "markAsReviewed" in html_content
        assert "goToNext" in html_content

    def test_no_changes_html(self):
        """Test HTML generation for no changes scenario."""
        plan_text = self.load_sample("sample_plan_3.txt")
        plan_summary = self.parser.parse(plan_text)

        html_content = self.renderer.create_standalone_html(plan_summary)

        # Should show no changes message
        assert "No changes. Infrastructure is up-to-date" in html_content
        assert "no-changes" in html_content

        # Should not have resource change sections
        assert "resource-changes" not in html_content

    def test_extract_resource_diff(self):
        """Test extraction of resource diff from raw plan."""
        plan_text = self.load_sample("sample_plan_1.txt")
        plan_summary = self.parser.parse(plan_text)

        # Get the first resource change
        resource_change = plan_summary.resource_changes[0]

        # Extract diff
        diff = self.renderer._extract_resource_diff(plan_text, resource_change)

        assert diff is not None
        assert len(diff) > 0
        # Should contain the resource address
        assert resource_change.resource_address in diff

    def test_html_escaping(self):
        """Test that HTML characters are properly escaped."""
        test_input = "< > & \" '"
        result = self.renderer._colorize_terraform_output(test_input)

        assert "&lt;" in result
        assert "&gt;" in result
        assert "&amp;" in result

    def test_escape_js_escapes_template_interpolation(self):
        """Test JS escaping prevents template literal interpolation."""
        test_input = "credentials: ${env:BASETEN_API_KEY}"

        result = str(self.renderer._escape_js(test_input))

        assert "\\${env:BASETEN_API_KEY}" in result

    def test_sensitive_value_rendering(self):
        """Test rendering of sensitive values."""
        plan_text = self.load_sample("sample_plan_2.txt")
        plan_summary = self.parser.parse(plan_text)

        html_content = self.renderer.create_standalone_html(plan_summary)

        # Should contain sensitive value styling
        assert "tf-sensitive" in html_content
        assert "(sensitive value)" in html_content

    def test_module_resource_rendering(self):
        """Test rendering of module resources."""
        plan_text = self.load_sample("sample_plan_2.txt")
        plan_summary = self.parser.parse(plan_text)

        html_content = self.renderer.create_standalone_html(plan_summary)

        # Should contain module resource addresses
        assert "module.database.aws_db_instance.postgres" in html_content
        assert "module.vpc.aws_vpc.main" in html_content

    def test_progress_tracking_elements(self):
        """Test that progress tracking elements are included."""
        plan_text = self.load_sample("sample_plan_1.txt")
        plan_summary = self.parser.parse(plan_text)

        html_content = self.renderer.create_standalone_html(plan_summary)

        # Check for progress elements
        assert "progress-bar" in html_content
        assert "progress-fill" in html_content
        assert "progress-text" in html_content
        assert "resources reviewed" in html_content

    def test_review_action_buttons(self):
        """Test that review action buttons are included."""
        plan_text = self.load_sample("sample_plan_1.txt")
        plan_summary = self.parser.parse(plan_text)

        html_content = self.renderer.create_standalone_html(plan_summary)

        # Check for action buttons
        assert "btn-approve" in html_content
        assert "btn-needs-changes" in html_content
        assert "btn-next" in html_content
        assert "Approve" in html_content
        assert "Needs Changes" in html_content
        assert "Next Change" in html_content

    def test_css_styling_included(self):
        """Test that CSS styling is included."""
        plan_text = self.load_sample("sample_plan_1.txt")
        plan_summary = self.parser.parse(plan_text)

        html_content = self.renderer.create_standalone_html(plan_summary)

        # Check for key CSS classes
        assert "resource-card" in html_content
        assert "resource-header" in html_content
        assert "resource-content" in html_content
        assert "tf-add" in html_content or "tf-delete" in html_content

    def test_javascript_functionality_included(self):
        """Test that JavaScript functionality is included."""
        plan_text = self.load_sample("sample_plan_1.txt")
        plan_summary = self.parser.parse(plan_text)

        html_content = self.renderer.create_standalone_html(plan_summary)

        # Check for key JavaScript functions
        assert "function toggleResource" in html_content
        assert "function markAsReviewed" in html_content
        assert "function goToNext" in html_content
        assert "function updateProgress" in html_content

        # Check for keyboard shortcuts
        assert "keydown" in html_content

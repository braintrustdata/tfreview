"""
Test cases for Terraform Plan Parser.
"""

import pytest
from pathlib import Path
from tfreview.parser import TerraformPlanParser, ChangeType, PlanSummary


class TestTerraformPlanParser:
    """Test cases for the terraform plan parser."""

    def setup_method(self):
        """Set up test fixtures."""
        self.parser = TerraformPlanParser()
        self.samples_dir = Path(__file__).parent.parent / "samples"

    def load_sample(self, filename: str) -> str:
        """Load a sample plan file."""
        return (self.samples_dir / filename).read_text(encoding="utf-8")

    def test_parse_sample_plan_1(self):
        """Test parsing sample plan 1 - basic create/update/delete."""
        plan_text = self.load_sample("sample_plan_1.txt")
        result = self.parser.parse(plan_text)

        assert isinstance(result, PlanSummary)
        assert result.has_changes
        assert result.to_add == 1
        assert result.to_change == 1
        assert result.to_destroy == 1
        assert len(result.resource_changes) == 3

        # Check specific resources
        resources_by_address = {
            rc.resource_address: rc for rc in result.resource_changes
        }

        # AWS instance creation
        assert "aws_instance.example" in resources_by_address
        instance = resources_by_address["aws_instance.example"]
        assert instance.change_type == ChangeType.CREATE
        assert instance.resource_type == "aws_instance"
        assert instance.resource_name == "example"

        # Security group update
        assert "aws_security_group.web" in resources_by_address
        sg = resources_by_address["aws_security_group.web"]
        assert sg.change_type == ChangeType.UPDATE
        assert sg.resource_type == "aws_security_group"
        assert sg.resource_name == "web"

        # S3 bucket deletion
        assert "aws_s3_bucket.legacy" in resources_by_address
        bucket = resources_by_address["aws_s3_bucket.legacy"]
        assert bucket.change_type == ChangeType.DELETE
        assert bucket.resource_type == "aws_s3_bucket"
        assert bucket.resource_name == "legacy"

    def test_parse_sample_plan_2(self):
        """Test parsing sample plan 2 - modules and sensitive values."""
        plan_text = self.load_sample("sample_plan_2.txt")
        result = self.parser.parse(plan_text)

        assert result.has_changes
        assert result.to_add == 1
        assert result.to_change == 2
        assert result.to_destroy == 1
        assert len(result.resource_changes) == 4

        # Check module resource
        resources_by_address = {
            rc.resource_address: rc for rc in result.resource_changes
        }
        assert "module.database.aws_db_instance.postgres" in resources_by_address

        db_instance = resources_by_address["module.database.aws_db_instance.postgres"]
        assert db_instance.change_type == ChangeType.CREATE
        assert db_instance.has_sensitive  # Should detect sensitive password

        # Check replacement resource
        assert "aws_route53_record.api[0]" in resources_by_address
        route53 = resources_by_address["aws_route53_record.api[0]"]
        assert route53.change_type == ChangeType.REPLACE

    def test_parse_sample_plan_3(self):
        """Test parsing sample plan 3 - no changes."""
        plan_text = self.load_sample("sample_plan_3.txt")
        result = self.parser.parse(plan_text)

        assert not result.has_changes
        assert result.to_add == 0
        assert result.to_change == 0
        assert result.to_destroy == 0
        assert len(result.resource_changes) == 0
        assert len(result.output_changes) == 0

    def test_parse_sample_plan_4(self):
        """Test parsing sample plan 4 - complex nested modules."""
        plan_text = self.load_sample("sample_plan_4.txt")
        result = self.parser.parse(plan_text)

        assert result.has_changes
        assert result.to_add == 1
        assert result.to_change == 3
        assert result.to_destroy == 2

        # Check nested module resource
        resources_by_address = {
            rc.resource_address: rc for rc in result.resource_changes
        }
        assert (
            "module.networking.module.security.aws_security_group.app[0]"
            in resources_by_address
        )

        nested_sg = resources_by_address[
            "module.networking.module.security.aws_security_group.app[0]"
        ]
        assert nested_sg.change_type == ChangeType.CREATE

        # Check indexed resource
        assert "aws_launch_template.web[2]" in resources_by_address
        launch_template = resources_by_address["aws_launch_template.web[2]"]
        assert launch_template.change_type == ChangeType.REPLACE

    def test_parse_sample_plan_5(self):
        """Test parsing sample plan 5 - data resources and outputs."""
        plan_text = self.load_sample("sample_plan_5.txt")
        result = self.parser.parse(plan_text)

        assert result.has_changes
        assert result.to_add == 1
        assert result.to_change == 1
        assert result.to_destroy == 0

        # Check that data resources are not included in resource changes
        # (they should be filtered out as they're not actual infrastructure changes)
        resources_by_address = {
            rc.resource_address: rc for rc in result.resource_changes
        }

        # Should have the instance and secret version, but not the data source
        assert "aws_instance.web_servers[0]" in resources_by_address
        assert "aws_secretsmanager_secret_version.db_password" in resources_by_address

        instance = resources_by_address["aws_instance.web_servers[0]"]
        assert instance.change_type == ChangeType.CREATE

        secret = resources_by_address["aws_secretsmanager_secret_version.db_password"]
        assert secret.change_type == ChangeType.UPDATE
        assert secret.has_sensitive

    def test_change_type_parsing(self):
        """Test parsing of different change type indicators."""
        test_cases = [
            ("will be created", ChangeType.CREATE),
            ("will be updated in-place", ChangeType.UPDATE),
            ("will be modified", ChangeType.UPDATE),
            ("will be destroyed", ChangeType.DELETE),
            ("will be replaced", ChangeType.REPLACE),
            ("unknown action", ChangeType.NO_OP),
        ]

        for action, expected_type in test_cases:
            result = self.parser._parse_change_type(action)
            assert result == expected_type

    def test_resource_address_parsing(self):
        """Test parsing of resource addresses."""
        test_cases = [
            ("aws_instance.example", ("aws_instance", "example")),
            ("module.vpc.aws_vpc.main", ("aws_vpc", "main")),
            (
                "module.database.module.subnet.aws_subnet.private[0]",
                ("aws_subnet", "private"),
            ),
            ("data.aws_ami.ubuntu", ("data.aws_ami", "ubuntu")),
        ]

        for address, expected in test_cases:
            resource_type, resource_name = self.parser._parse_resource_address(address)
            assert (resource_type, resource_name) == expected

    def test_sensitive_value_detection(self):
        """Test detection of sensitive values."""
        plan_text = self.load_sample("sample_plan_2.txt")
        result = self.parser.parse(plan_text)

        # Find the database instance
        db_instance = None
        for rc in result.resource_changes:
            if "postgres" in rc.resource_address:
                db_instance = rc
                break

        assert db_instance is not None
        assert db_instance.has_sensitive

    def test_computed_value_detection(self):
        """Test detection of computed values."""
        plan_text = self.load_sample("sample_plan_1.txt")
        result = self.parser.parse(plan_text)

        # Find the instance
        instance = None
        for rc in result.resource_changes:
            if "aws_instance.example" == rc.resource_address:
                instance = rc
                break

        assert instance is not None
        assert instance.has_computed

    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Empty plan
        empty_result = self.parser.parse("")
        assert not empty_result.has_changes

        # Plan with only whitespace
        whitespace_result = self.parser.parse("   \n\n   ")
        assert not whitespace_result.has_changes

        # Plan with malformed content (should not crash)
        malformed_result = self.parser.parse("This is not a terraform plan")
        assert not malformed_result.has_changes

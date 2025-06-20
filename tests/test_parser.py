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
        return (self.samples_dir / filename).read_text(encoding='utf-8')
    
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
        resources_by_address = {rc.resource_address: rc for rc in result.resource_changes}
        
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
        resources_by_address = {rc.resource_address: rc for rc in result.resource_changes}
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
        resources_by_address = {rc.resource_address: rc for rc in result.resource_changes}
        assert "module.networking.module.security.aws_security_group.app[0]" in resources_by_address
        
        nested_sg = resources_by_address["module.networking.module.security.aws_security_group.app[0]"]
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
        resources_by_address = {rc.resource_address: rc for rc in result.resource_changes}
        
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
            ("module.database.module.subnet.aws_subnet.private[0]", ("aws_subnet", "private")),
            ("data.aws_ami.ubuntu", ("data.aws_ami", "ubuntu")),
        ]
        
        for address, expected in test_cases:
            resource_type, resource_name = self.parser._parse_resource_address(address)
            assert (resource_type, resource_name) == expected
    
    def test_json_serialization(self):
        """Test JSON serialization of plan summary."""
        plan_text = self.load_sample("sample_plan_1.txt")
        result = self.parser.parse(plan_text)
        
        json_output = self.parser.to_json(result)
        assert isinstance(json_output, str)
        
        # Should be valid JSON
        import json
        parsed = json.loads(json_output)
        assert parsed["has_changes"] is True
        assert parsed["to_add"] == 1
        assert parsed["to_change"] == 1
        assert parsed["to_destroy"] == 1
        assert len(parsed["resource_changes"]) == 3
    
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
        # Empty plan - should now be detected as an error
        empty_result = self.parser.parse("")
        assert empty_result.has_errors
        assert not empty_result.has_changes
        
        # Plan with only whitespace - should now be detected as an error
        whitespace_result = self.parser.parse("   \n\n   ")
        assert whitespace_result.has_errors
        assert not whitespace_result.has_changes
        
        # Plan with malformed content - should now be detected as an error
        malformed_result = self.parser.parse("This is not a terraform plan")
        assert malformed_result.has_errors
        assert not malformed_result.has_changes

    def test_no_changes_detection(self):
        """Test detection of 'no changes' plan."""
        plan_text = """
Terraform used the selected providers to generate the following execution plan.

No changes. Infrastructure is up-to-date.

This means that Terraform did not detect any differences between your
configuration and the remote system state. As a result, there are no
actions to take.
        """
        
        result = self.parser.parse(plan_text)
        assert not result.has_changes
        assert not result.has_errors
        assert len(result.error_messages) == 0
        assert result.to_add == 0
        assert result.to_change == 0
        assert result.to_destroy == 0
    
    def test_error_detection_generic(self):
        """Test detection of generic terraform errors."""
        plan_text = """
Error: Invalid character

  on main.tf line 46, in resource "aws_instance" "web_app":
 46:     Name = $var.name-web_app

This character is not used within the language.

Error: Invalid expression

  on main.tf line 46, in resource "aws_instance" "web_app":
  46:     Name = $var.name-web_app

Expected the start of an expression, but found an invalid expression token.
        """
        
        result = self.parser.parse(plan_text)
        assert result.has_errors
        assert not result.has_changes
        assert len(result.error_messages) > 0
        assert result.to_add == 0
        assert result.to_change == 0
        assert result.to_destroy == 0
        
        # Should contain error information
        error_text = ' '.join(result.error_messages).lower()
        assert 'error' in error_text
    
    def test_error_detection_authentication(self):
        """Test detection of authentication errors."""
        plan_text = """
╷
│ Error: No valid credential sources found for AWS Provider.
│ 
│   on main.tf line 1, in provider "aws":
│    1: provider "aws" {
│ 
│ Please see https://registry.terraform.io/providers/hashicorp/aws
│ for more information about providing credentials.
│ 
│ Error: failed to refresh cached credentials, no EC2 IMDS role found,
│ operation error ec2imds: GetMetadata, request send failed, Get
│ "http://169.254.169.254/latest/meta-data/iam/security-credentials/": dial tcp
│ 169.254.169.254:80: connect: network is unreachable
╵
        """
        
        result = self.parser.parse(plan_text)
        assert result.has_errors
        assert not result.has_changes
        assert len(result.error_messages) > 0
        
        # Should detect credential errors
        error_text = ' '.join(result.error_messages).lower()
        assert 'credential' in error_text or 'error' in error_text
    
    def test_error_detection_access_denied(self):
        """Test detection of access denied errors.""" 
        plan_text = """
Error creating IAM Role: AccessDenied: User: arn:aws:iam::123456789012:user/terraform 
is not authorized to perform: iam:CreateRole on resource: role test-role

        """
        
        result = self.parser.parse(plan_text)
        assert result.has_errors
        assert not result.has_changes
        assert len(result.error_messages) > 0
        
        # Should detect access denied
        error_text = ' '.join(result.error_messages).lower()
        assert 'accessdenied' in error_text
    
    def test_error_detection_provider_not_found(self):
        """Test detection of provider errors."""
        plan_text = """
Error: Failed to install provider

Provider registry.terraform.io/hashicorp/nonexistent does not exist or
you may not have access to it.
        """
        
        result = self.parser.parse(plan_text)
        assert result.has_errors
        assert not result.has_changes
        assert len(result.error_messages) > 0
        
        # Should detect provider failure
        error_text = ' '.join(result.error_messages).lower()
        assert 'failed' in error_text or 'error' in error_text
    
    def test_error_detection_cycle_error(self):
        """Test detection of dependency cycle errors."""
        plan_text = """
Error: Cycle: aws_security_group.sg_ping, aws_security_group.sg_8080
        """
        
        result = self.parser.parse(plan_text)
        assert result.has_errors
        assert not result.has_changes
        assert len(result.error_messages) > 0
        
        # Should detect cycle
        error_text = ' '.join(result.error_messages).lower()
        assert 'cycle' in error_text
    
    def test_valid_plan_with_changes(self):
        """Test parsing a valid plan with changes."""
        plan_text = """
Terraform used the selected providers to generate the following execution plan. Resource actions are indicated with the following symbols:
  + create

Terraform will perform the following actions:

  # aws_instance.example will be created
  + resource "aws_instance" "example" {
      + ami                                  = "ami-0c02fb55956c7d316"
      + arn                                  = (known after apply)
      + associate_public_ip_address          = (known after apply)
      + availability_zone                    = (known after apply)
      + cpu_core_count                       = (known after apply)
      + cpu_threads_per_core                 = (known after apply)
      + disable_api_stop                     = (known after apply)
      + disable_api_termination              = (known after apply)
      + ebs_optimized                        = (known after apply)
      + get_password_data                    = false
      + host_id                              = (known after apply)
      + id                                   = (known after apply)
      + instance_initiated_shutdown_behavior = (known after apply)
      + instance_state                       = (known after apply)
      + instance_type                        = "t2.micro"
      + ipv6_address_count                   = (known after apply)
      + ipv6_addresses                       = (known after apply)
      + key_name                             = (known after apply)
      + monitoring                           = (known after apply)
      + outpost_arn                          = (known after apply)
      + password_data                        = (known after apply)
      + placement_group                      = (known after apply)
      + placement_partition_number           = (known after apply)
      + primary_network_interface_id         = (known after apply)
      + private_dns_name_options             = (known after apply)
      + private_ip                           = (known after apply)
      + public_dns                           = (known after apply)
      + public_ip                            = (known after apply)
      + secondary_private_ips                = (known after apply)
      + security_groups                      = (known after apply)
      + source_dest_check                    = true
      + subnet_id                            = (known after apply)
      + tags_all                             = (known after apply)
      + tenancy                              = (known after apply)
      + user_data                            = (known after apply)
      + user_data_base64                     = (known after apply)
      + user_data_replace_on_change          = false
      + vpc_security_group_ids               = (known after apply)
    }

Plan: 1 to add, 0 to change, 0 to destroy.
        """
        
        result = self.parser.parse(plan_text)
        assert not result.has_errors
        assert result.has_changes
        assert len(result.error_messages) == 0
        assert result.to_add == 1
        assert result.to_change == 0
        assert result.to_destroy == 0
        assert len(result.resource_changes) == 1
    
    def test_mixed_error_and_plan_prioritizes_error(self):
        """Test that errors take priority over plan content."""
        plan_text = """
Error: Invalid configuration

  on main.tf line 10:
  10: invalid syntax here

Expected a resource or data block.

Terraform used the selected providers to generate the following execution plan.

  # aws_instance.example will be created
  + resource "aws_instance" "example" {
      + instance_type = "t2.micro"
    }

Plan: 1 to add, 0 to change, 0 to destroy.
        """
        
        result = self.parser.parse(plan_text)
        assert result.has_errors
        # When errors are detected, has_changes should be False
        assert not result.has_changes
        assert len(result.error_messages) > 0
        # Counters should be 0 when errors are detected
        assert result.to_add == 0
        assert result.to_change == 0
        assert result.to_destroy == 0

    def test_empty_plan_detection(self):
        """Test detection of empty terraform plan output."""
        # Test completely empty input
        result = self.parser.parse("")
        assert result.has_errors
        assert not result.has_changes
        assert len(result.error_messages) > 0
        assert "empty" in ' '.join(result.error_messages).lower()
        
        # Test whitespace-only input
        result = self.parser.parse("   \n\n   ")
        assert result.has_errors
        assert not result.has_changes
        assert "empty" in ' '.join(result.error_messages).lower()
    
    def test_too_short_plan_detection(self):
        """Test detection of too short terraform plan output."""
        # Very short input that doesn't look like terraform
        result = self.parser.parse("short")
        assert result.has_errors
        assert not result.has_changes
        assert "too short" in ' '.join(result.error_messages).lower()
        
        # Slightly longer but still too short
        result = self.parser.parse("This is not terraform output")
        assert result.has_errors
        assert not result.has_changes
        assert any(keyword in ' '.join(result.error_messages).lower() 
                  for keyword in ["too short", "does not appear"])
    
    def test_insufficient_content_detection(self):
        """Test detection of plans with insufficient content."""
        # Only one meaningful line
        result = self.parser.parse("Just one line")
        assert result.has_errors
        assert not result.has_changes
        assert "insufficient" in ' '.join(result.error_messages).lower()
        
        # Two lines but not terraform-like
        result = self.parser.parse("Line one\nLine two")
        assert result.has_errors
        assert not result.has_changes
    
    def test_invalid_plan_format_detection(self):
        """Test detection of input that doesn't look like terraform output."""
        # Random text that's long enough but not terraform
        non_terraform_text = """
This is some random text that is long enough to pass the length check
but it doesn't contain any terraform-specific keywords or patterns
so it should be detected as invalid terraform plan output.
It has multiple lines and sufficient content but is clearly not terraform.
        """
        
        result = self.parser.parse(non_terraform_text)
        assert result.has_errors
        assert not result.has_changes
        assert "does not appear" in ' '.join(result.error_messages).lower()
    
    def test_incomplete_plan_detection(self):
        """Test detection of incomplete terraform plans."""
        # Short text that mentions terraform but seems incomplete
        incomplete_plan = """
Terraform will perform some actions
But this output seems incomplete
        """
        
        result = self.parser.parse(incomplete_plan)
        assert result.has_errors
        assert not result.has_changes
        assert any(keyword in ' '.join(result.error_messages).lower() 
                  for keyword in ["incomplete", "invalid"])
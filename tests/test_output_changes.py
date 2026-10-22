"""Output-only plans must remain visible in HTML and Atlantis summaries."""

import pytest
from tfreview.parser import TerraformPlanParser
from tfreview.renderer import HTMLRenderer
from tfreview.cli import format_plan_summary

OLD = "266be81d2b9862c43fd5d93e9a2308f1d5122c3f"
NEW = "17af63dbc0eb464564b6b618b447cd061c377a82"


@pytest.mark.parametrize("heading", ["Changes to Outputs:", "Outputs:"])
def test_scalar_sha_output(heading):
    plan = TerraformPlanParser().parse(
        f'{heading}\n  ~ version = "{OLD}" -> "{NEW}"\n\n'
        "You can apply this plan to save these new output values.\n"
        "Saved the plan to: /tmp/plan=not-an-output\n"
    )
    assert plan.has_changes
    assert len(plan.output_changes) == 1
    output = plan.output_changes[0]
    assert output.name == "version"
    assert output.old_value == f'"{OLD}"'
    assert output.new_value == f'"{NEW}"'
    assert "Saved the plan" not in output.diff_text
    assert (
        format_plan_summary(plan)
        == "Plan Summary: 1 output changed; no resource changes."
    )
    html = HTMLRenderer().create_standalone_html(plan)
    assert OLD in html and NEW in html
    assert 'id="output-changes"' in html
    assert "✅ No changes. Infrastructure is up-to-date." not in html


def test_nested_outputs_count_once_and_preserve_diffs():
    plan = TerraformPlanParser().parse(f"""Changes to Outputs:
  ~ app_deployment = {{
      ~ version = "{OLD}" -> "{NEW}"
      ~ helm_values = {{
          ~ images = {{
              ~ api = {{
                  ~ tag = "{OLD}" -> "{NEW}"
                }}
            }}
        }}
    }}
  + enabled = true
  - retired = "old" -> null
  ~ secret = (sensitive value)

─────────────────────────────────
Saved the plan to: /tmp/foo=bar
""")
    assert [o.name for o in plan.output_changes] == [
        "app_deployment",
        "enabled",
        "retired",
        "secret",
    ]
    assert "helm_values" in plan.output_changes[0].diff_text
    assert plan.output_changes[-1].is_sensitive
    assert "(sensitive value)" in plan.output_changes[-1].diff_text
    assert (
        format_plan_summary(plan)
        == "Plan Summary: 4 outputs changed; no resource changes."
    )


def test_resource_parser_stops_before_outputs():
    plan = TerraformPlanParser().parse(
        """  # aws_instance.example will be updated in-place
  ~ resource "aws_instance" "example" {
      ~ instance_type = "t3.small" -> "t3.medium"
    }

Changes to Outputs:
  ~ version = "old" -> "new"
"""
    )
    assert len(plan.resource_changes) == 1
    assert len(plan.output_changes) == 1
    assert format_plan_summary(plan) == "Plan Summary: 1 to change, 1 output changed."
    assert "Changes to Outputs:" not in HTMLRenderer()._extract_resource_diff(
        plan.raw_plan, plan.resource_changes[0]
    )


def test_genuinely_unchanged_plan():
    plan = TerraformPlanParser().parse(
        "No changes. Your infrastructure matches the configuration."
    )
    assert not plan.has_changes
    assert not plan.output_changes
    assert format_plan_summary(plan) == "Plan Summary: No changes."

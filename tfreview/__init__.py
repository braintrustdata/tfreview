"""
TFReview - A tool for reviewing Terraform plans in a nice HTML interface.
"""

__version__ = "1.0.0"
__author__ = "TFReview Team"
__email__ = "team@tfreview.dev"

from .parser import TerraformPlanParser
from .renderer import HTMLRenderer
from .cli import main

__all__ = ["TerraformPlanParser", "HTMLRenderer", "main"]
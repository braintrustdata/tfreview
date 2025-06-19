"""
Setup script for TFReview package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read version from __init__.py
init_file = Path(__file__).parent / "tfreview" / "__init__.py"
version = "1.0.0"
if init_file.exists():
    for line in init_file.read_text().splitlines():
        if line.startswith("__version__"):
            version = line.split('"')[1]
            break

setup(
    name="tfreview",
    version=version,
    author="TFReview Team",
    author_email="team@tfreview.dev",
    description="A tool for reviewing Terraform plans in a nice HTML interface",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tfreview/tfreview",
    packages=find_packages(),
    include_package_data=True,
    package_data={
        "tfreview": [
            "templates/*.html",
            "templates/*.css",
            "templates/*.js",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: Web Environment", 
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
    python_requires=">=3.8",
    install_requires=[
        "jinja2>=3.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=4.0.0",
            "mypy>=0.991",
        ],
    },
    entry_points={
        "console_scripts": [
            "tfreview=tfreview.cli:main",
        ],
    },
    keywords="terraform plan review html infrastructure devops",
    project_urls={
        "Bug Reports": "https://github.com/tfreview/tfreview/issues",
        "Source": "https://github.com/tfreview/tfreview",
        "Documentation": "https://github.com/tfreview/tfreview/blob/main/README.md",
    },
)
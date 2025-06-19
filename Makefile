.PHONY: help install install-dev test lint format clean build publish

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install the package
	pip install -e .

install-dev:  ## Install development dependencies
	pip install -e ".[dev]"

test:  ## Run tests
	pytest tests/ -v

test-cov:  ## Run tests with coverage
	pytest tests/ -v --cov=tfreview --cov-report=html --cov-report=term

lint:  ## Run linting
	flake8 tfreview/ tests/
	mypy tfreview/

format:  ## Format code
	black tfreview/ tests/

format-check:  ## Check code formatting
	black --check tfreview/ tests/

clean:  ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

build:  ## Build the package
	python setup.py sdist bdist_wheel

publish:  ## Publish to PyPI (requires authentication)
	python -m twine upload dist/*

demo:  ## Run demo with sample plan
	python -m tfreview.cli samples/sample_plan_1.txt -o demo.html

test-all-samples:  ## Test all sample plans
	python -m tfreview.cli samples/sample_plan_1.txt -o test_sample_1.html --no-browser
	python -m tfreview.cli samples/sample_plan_2.txt -o test_sample_2.html --no-browser
	python -m tfreview.cli samples/sample_plan_3.txt -o test_sample_3.html --no-browser
	python -m tfreview.cli samples/sample_plan_4.txt -o test_sample_4.html --no-browser
	python -m tfreview.cli samples/sample_plan_5.txt -o test_sample_5.html --no-browser
	@echo "All sample HTML files generated successfully!"
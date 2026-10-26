.PHONY: help test validate bundle clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-10s %s\n", $$1, $$2}'

test: ## Run the test suite (needs local tests/forbidden_terms.txt, see README)
	python3 -m unittest discover -s tests

validate: ## Validate the three sample surveys with fresh-file rules
	python3 skills/survey-qsf/scripts/validate_qsf.py skills/survey-qsf/samples/*.qsf --fresh

bundle: ## Build dist/survey-skill-bundle.txt (single-file upload for AI services)
	scripts/make_bundle.sh

clean: ## Remove bundle output and Python caches
	rm -rf dist/ skills/survey-qsf/scripts/__pycache__ tests/__pycache__

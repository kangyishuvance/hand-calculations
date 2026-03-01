NOTEBOOK ?= General_template.ipynb
OUTDIR ?= ./exports
NAME ?=

.PHONY: help report

help:
	@echo "Targets:"
	@echo "  make report NOTEBOOK=<file.ipynb> [OUTDIR=./exports] [NAME=custom_report_name]"
	@echo ""
	@echo "Examples:"
	@echo "  make report NOTEBOOK=Bearing_capacity_check.ipynb"
	@echo "  make report NOTEBOOK=General_template.ipynb OUTDIR=./exports NAME=General_template_report"

report:
	@if [ -n "$(NAME)" ]; then \
		./scripts/export_report.sh "$(NOTEBOOK)" "$(OUTDIR)" "$(NAME)"; \
	else \
		./scripts/export_report.sh "$(NOTEBOOK)" "$(OUTDIR)"; \
	fi

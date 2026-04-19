NOTEBOOK ?= General_template.ipynb
OUTDIR ?= ./exports
NAME ?=
ORIENTATION ?=

.PHONY: help report

help:
	@echo "Targets:"
	@echo "  make report NOTEBOOK=<file.ipynb> [OUTDIR=./exports] [NAME=custom_report_name] [ORIENTATION=landscape|portrait]"
	@echo ""
	@echo "Examples:"
	@echo "  make report NOTEBOOK=Bearing_capacity_check.ipynb"
	@echo "  make report NOTEBOOK=General_template.ipynb OUTDIR=./exports NAME=General_template_report"
	@echo "  make report NOTEBOOK=Bearing_capacity_check.ipynb ORIENTATION=landscape"

report:
	@cmd="./scripts/export_report.sh \"$(NOTEBOOK)\" \"$(OUTDIR)\""; \
	if [ -n "$(NAME)" ]; then \
		cmd="$$cmd \"$(NAME)\""; \
	fi; \
	if [ -n "$(ORIENTATION)" ]; then \
		if [ "$(ORIENTATION)" = "landscape" ]; then \
			cmd="$$cmd --landscape"; \
		elif [ "$(ORIENTATION)" = "portrait" ]; then \
			cmd="$$cmd --portrait"; \
		fi; \
	fi; \
	eval "$$cmd"

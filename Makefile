export PATH := /snap/bin:$(PATH)

# TARGETS
lint: ## Run linter
	tox -e lint

clean: ## Remove .tox and build dirs
	rm -rf .tox/
	rm -rf venv/
	rm -rf *.charm

deploy-focal: ## deploy focal
	@./scripts/deploy-focal.sh

deploy-bionic: ## deploy bionic
	@./scripts/deploy-bionic.sh

deploy-centos7: ## deploy centos7
	@./scripts/deploy-centos7.sh

deploy-local: ## deploy lxd
	@./scripts/deploy-local.sh

relate: ## deploy centos7
	@./scripts/relate.sh


charms: ## Build all charms
	@charmcraft build --from charm-slurmd
	@charmcraft build --from charm-slurm-configurator
	@charmcraft build --from charm-slurmctld
	@charmcraft build --from charm-slurmdbd

# Display target comments in 'make help'
help: 
	grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# SETTINGS
# Use one shell for all commands in a target recipe
.ONESHELL:
# Set default goal
.DEFAULT_GOAL := help
# Use bash shell in Make instead of sh 
SHELL := /bin/bash

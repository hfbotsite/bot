PROJECT_NAME := $(shell python setup.py --name)
PROJECT_VERSION := $(shell python setup.py --version)

SHELL := /bin/bash
BOLD := \033[1m
DIM := \033[2m
RESET := \033[0m

reinstall: uninstall install clean

.PHONY: install
install:
	@echo -e "$(BOLD)Installing $(PROJECT_NAME) $(PROJECT_VERSION)$(RESET)"
	@echo -e -n "$(DIM)"
	@pip3 install .
	@echo -e -n "$(RESET)"

.PHONY: uninstall
uninstall:
	@echo -e "$(BOLD)Uninstalling '$(PROJECT_NAME)'$(RESET)"
	-@pip3 uninstall -y $(PROJECT_NAME) 2> /dev/null

.PHONY: lint
lint:
	@echo -e "$(BOLD)Analyzing code for $(PROJECT_NAME) $(PROJECT_VERSION)$(RESET)"
	-@pylint bin/* src/**/*.py \
		--output-format text --reports no \
		--msg-template "{path}:{line:04d}:{obj} {msg} ({msg_id})" \
		| sort | awk \
			'/[RC][0-9]{4}/ {print "\033[2m" $$0 "\033[0m"};\
			 /[EF][0-9]{4}/ {print "\033[1m" $$0 "\033[0m"};\
			 /W[0-9]{4}/ {print};'

.PHONY: doc
doc:
	@echo -e "$(BOLD)Building documentation for $(PROJECT_NAME) $(PROJECT_VERSION)$(RESET)"
	@echo -e -n "$(DIM)"
	@cd doc && $(MAKE) html
	@echo -e -n "$(RESET)"

.PHONY: dist
dist:
	@echo -e "$(BOLD)Packaging $(PROJECT_NAME) $(PROJECT_VERSION)$(RESET)"
	@echo -e -n "$(DIM)"
	@python setup.py sdist --formats=zip --dist-dir=dist
	@echo -e -n "$(RESET)"

.PHONY: clean
clean:
	@echo -e "$(BOLD)Cleaning $(PROJECT_NAME) $(PROJECT_VERSION) project$(RESET)"
	@rm -rf build dist $(PROJECT_NAME).egg-info
	@sh ./scripts/prune_cache.sh
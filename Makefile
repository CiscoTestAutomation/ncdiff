###############################################################################
#                            yang Internal Makefile
#
# Author:
#   Jonathan Yang (yuekyang) - CSG Polaris DMI Infra
#
# Support:
#	yang-python@cisco.com
#
# Version:
#   v2.0.0
#
# Date:
#   May 2018
#
# About This File:
#   This script will build the dyntopo package for distribution in PyPI server
#
# Requirements:
#	1. Module name is the same as package name.
#	2. setup.py file is stored within the module folder
###############################################################################

# Variables
PKG_NAME      = ncdiff
PKG_PATH      = ncdiff
BUILDDIR      = $(shell pwd)/__build__
PYTHON        = python
TESTCMD       = cd tests; runAll
DISTDIR       = $(BUILDDIR)/dist

.PHONY: clean package develop undevelop populate_dist_dir help \
        docs test

help:
	@echo "Please use 'make <target>' where <target> is one of"
	@echo ""
	@echo "package          : Build the package"
	@echo "test             : Test the package"
	@echo "clean            : Remove build artifacts"
	@echo "develop          : Build and install development package"
	@echo "undevelop        : Uninstall development package"
	@echo "docs             : Build Sphinx documentation for this package"

docs:
	@echo ""
	@echo "--------------------------------------------------------------------"
	@echo "Building $(PKG_NAME) documentation for preview: $@"
	@echo ""

	@./setup.py docs

	@echo "Completed building docs for preview."
	@echo ""

test:
	@$(TESTCMD)

package:
	@echo ""
	@echo "--------------------------------------------------------------------"
	@echo "Building $(PKG_NAME) distributable: $@"
	@echo ""

	@./setup.py bdist_wheel --dist-dir=$(DISTDIR)

	@echo "Completed building: $@"
	@echo ""

develop:
	@echo ""
	@echo "--------------------------------------------------------------------"
	@echo "Building and installing $(PKG_NAME) development distributable: $@"
	@echo ""
	@pip3 uninstall -y ncdiff
	@python3 setup.py develop --no-deps -q

	@echo "Completed building and installing: $@"
	@echo ""

undevelop:
	@echo ""
	@echo "--------------------------------------------------------------------"
	@echo "Uninstalling $(PKG_NAME) development distributable: $@"
	@echo ""

	@./setup.py develop --no-deps -q --uninstall

	@echo "Completed uninstalling: $@"
	@echo ""

clean:
	@echo ""
	@echo "--------------------------------------------------------------------"
	@echo "Removing make directory: $(BUILDDIR)"
	@rm -rf $(BUILDDIR)
	@echo "Removing build artifacts ..."
	@./setup.py clean
	@echo ""
	@echo "Done."
	@echo ""

# StreamController RPM Build Makefile

PACKAGE_NAME := streamcontroller
SPEC_FILE := StreamController.spec
BUILD_SCRIPT := build_rpm.sh
BUILD_DIR := $(HOME)/rpmbuild
PROJECT_ROOT := $(shell cd .. && pwd)

# Extract version from spec file
VERSION := $(shell grep "^Version:" $(SPEC_FILE) | awk '{print $$2}')
RELEASE := $(shell grep "^Release:" $(SPEC_FILE) | awk '{print $$2}' | cut -d'%' -f1)

.PHONY: help rpm srpm clean install check-deps test-rpm

help:
	@echo "StreamController RPM Build Targets:"
	@echo "=================================="
	@echo "  rpm        - Build binary RPM package"
	@echo "  srpm       - Build source RPM package only"
	@echo "  clean      - Clean build artifacts"
	@echo "  install    - Install built RPM package"
	@echo "  check-deps - Check build dependencies"
	@echo "  test-rpm   - Test built RPM package"
	@echo "  help       - Show this help message"
	@echo ""
	@echo "Package: $(PACKAGE_NAME) v$(VERSION)-$(RELEASE)"
	@echo "Build directory: $(BUILD_DIR)"

check-deps:
	@echo "Checking build dependencies..."
	@command -v rpmbuild >/dev/null 2>&1 || { echo "Error: rpmbuild not found. Install: sudo dnf install rpm-build"; exit 1; }
	@command -v desktop-file-validate >/dev/null 2>&1 || { echo "Error: desktop-file-validate not found. Install: sudo dnf install desktop-file-utils"; exit 1; }
	@python3 --version >/dev/null 2>&1 || { echo "Error: python3 not found"; exit 1; }
	@python3 -c "import wheel" >/dev/null 2>&1 || { echo "Error: python3-wheel not found. Install: sudo dnf install python3-wheel"; exit 1; }
	@echo "✓ All build dependencies satisfied"

rpm: check-deps
	@echo "Building RPM package..."
	@chmod +x $(BUILD_SCRIPT)
	./$(BUILD_SCRIPT)

srpm: check-deps
	@echo "Building source RPM only..."
	@mkdir -p $(BUILD_DIR)/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
	
	# Create source tarball
	@echo "Creating source tarball..."
	@TEMP_DIR=$$(mktemp -d) && \
	SOURCE_DIR="$$TEMP_DIR/$(PACKAGE_NAME)-$(VERSION)" && \
	mkdir -p "$$SOURCE_DIR" && \
	cd "$(PROJECT_ROOT)" && \
	rsync -av \
		--exclude='.git*' --exclude='rpm/' --exclude='flatpak/' \
		--exclude='__pycache__/' --exclude='*.pyc' --exclude='.pytest_cache/' \
		--exclude='venv/' --exclude='env/' --exclude='.vscode/' \
		--exclude='*.egg-info/' --exclude='build/' --exclude='dist/' \
		./ "$$SOURCE_DIR/" && \
	cd "$$TEMP_DIR" && \
	tar -czf "$(BUILD_DIR)/SOURCES/$(PACKAGE_NAME)-$(VERSION).tar.gz" "$(PACKAGE_NAME)-$(VERSION)/" && \
	rm -rf "$$TEMP_DIR"
	
	# Copy spec file and build SRPM
	@cp $(SPEC_FILE) $(BUILD_DIR)/SPECS/
	@rpmbuild -bs $(BUILD_DIR)/SPECS/StreamController.spec \
		--define "_topdir $(BUILD_DIR)" \
		--define "_version $(VERSION)"
	
	@echo "Source RPM built: $$(find $(BUILD_DIR)/SRPMS -name '$(PACKAGE_NAME)-$(VERSION)-*.src.rpm')"

clean:
	@echo "Cleaning build artifacts..."
	@rm -rf $(BUILD_DIR)/BUILD/$(PACKAGE_NAME)*
	@rm -rf $(BUILD_DIR)/BUILDROOT/$(PACKAGE_NAME)*
	@rm -f $(BUILD_DIR)/SOURCES/$(PACKAGE_NAME)-$(VERSION).tar.gz
	@rm -f $(BUILD_DIR)/SPECS/StreamController.spec
	@rm -f $(BUILD_DIR)/SRPMS/$(PACKAGE_NAME)-$(VERSION)-*.src.rpm
	@rm -f $(BUILD_DIR)/RPMS/*/$(PACKAGE_NAME)-$(VERSION)-*.rpm
	@echo "✓ Build artifacts cleaned"

install: rpm
	@RPM_FILE=$$(find $(BUILD_DIR)/RPMS -name '$(PACKAGE_NAME)-$(VERSION)-*.rpm' | head -1) && \
	if [ -n "$$RPM_FILE" ]; then \
		echo "Installing $$RPM_FILE..."; \
		sudo dnf install -y "$$RPM_FILE"; \
		echo "✓ Package installed successfully"; \
		echo "Run 'streamcontroller' to start the application"; \
	else \
		echo "Error: No RPM file found to install"; \
		exit 1; \
	fi

test-rpm: rpm
	@RPM_FILE=$$(find $(BUILD_DIR)/RPMS -name '$(PACKAGE_NAME)-$(VERSION)-*.rpm' | head -1) && \
	if [ -n "$$RPM_FILE" ]; then \
		echo "Testing RPM package: $$RPM_FILE"; \
		echo ""; \
		echo "Package information:"; \
		rpm -qip "$$RPM_FILE"; \
		echo ""; \
		echo "Dependencies:"; \
		rpm -qRp "$$RPM_FILE"; \
		echo ""; \
		echo "File list (first 20 files):"; \
		rpm -qlp "$$RPM_FILE" | head -20; \
		echo ""; \
		echo "Package validation:"; \
		rpmlint "$$RPM_FILE" || true; \
	else \
		echo "Error: No RPM file found to test"; \
		exit 1; \
	fi

.PHONY: version-info
version-info:
	@echo "Package Information:"
	@echo "==================="
	@echo "Name:    $(PACKAGE_NAME)"
	@echo "Version: $(VERSION)"
	@echo "Release: $(RELEASE)"
	@echo "Spec:    $(SPEC_FILE)"
	@echo "Script:  $(BUILD_SCRIPT)"

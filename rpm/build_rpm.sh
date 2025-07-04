#!/bin/bash

# StreamController RPM Build Script
# This script creates a complete RPM package for StreamController

set -e  # Exit on any error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
RPM_DIR="$SCRIPT_DIR"
BUILD_DIR="${BUILD_DIR:-$HOME/rpmbuild}"
SPEC_FILE="$RPM_DIR/StreamController.spec"

# Extract version from spec file
VERSION=$(grep "^Version:" "$SPEC_FILE" | awk '{print $2}')
RELEASE=$(grep "^Release:" "$SPEC_FILE" | awk '{print $2}' | cut -d'%' -f1)
PACKAGE_NAME="streamcontroller"

echo "StreamController RPM Build Script"
echo "=================================="
echo "Package: $PACKAGE_NAME"
echo "Version: $VERSION"
echo "Release: $RELEASE"
echo "Source:  $REPO_ROOT"
echo "Build:   $BUILD_DIR"
echo ""

# Check prerequisites
echo "Checking prerequisites..."

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Warning: Not in a git repository. Continuing anyway..."
fi

# Check for required tools
REQUIRED_TOOLS=("rpmbuild" "desktop-file-validate")
for tool in "${REQUIRED_TOOLS[@]}"; do
    if ! command -v "$tool" &> /dev/null; then
        echo "Error: Required tool '$tool' not found."
        echo "Please install: sudo dnf install rpm-build desktop-file-utils"
        exit 1
    fi
done

# Check for Python
if ! python3 --version &> /dev/null; then
    echo "Error: Python 3 not found."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Using Python $PYTHON_VERSION"

# Create RPM build environment
echo "Setting up RPM build environment..."
mkdir -p "$BUILD_DIR"/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# Clean previous builds
echo "Cleaning previous builds..."
rm -f "$BUILD_DIR/SOURCES/${PACKAGE_NAME}-${VERSION}.tar.gz"
rm -f "$BUILD_DIR/SPECS/$(basename "$SPEC_FILE")"

# Create source tarball
echo "Creating source tarball..."
TEMP_DIR=$(mktemp -d)
SOURCE_DIR="$TEMP_DIR/${PACKAGE_NAME}-${VERSION}"

# Copy source files, excluding unnecessary directories
mkdir -p "$SOURCE_DIR"
rsync -av \
    --exclude='.git*' \
    --exclude='rpm/' \
    --exclude='flatpak/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache/' \
    --exclude='venv/' \
    --exclude='env/' \
    --exclude='.vscode/' \
    --exclude='*.egg-info/' \
    --exclude='build/' \
    --exclude='dist/' \
    "$REPO_ROOT/" "$SOURCE_DIR/"

# Create tarball
cd "$TEMP_DIR"
tar -czf "$BUILD_DIR/SOURCES/${PACKAGE_NAME}-${VERSION}.tar.gz" "${PACKAGE_NAME}-${VERSION}/"

# Clean up temp directory
rm -rf "$TEMP_DIR"

# Copy spec file
cp "$SPEC_FILE" "$BUILD_DIR/SPECS/"

# Build the RPM
echo "Building RPM package..."
cd "$BUILD_DIR"

# Build source RPM first
echo "Building source RPM..."
rpmbuild -bs "SPECS/$(basename "$SPEC_FILE")" \
    --define "_topdir $BUILD_DIR" \
    --define "_version $VERSION"

# Build binary RPM
echo "Building binary RPM..."
rpmbuild -bb "SPECS/$(basename "$SPEC_FILE")" \
    --define "_topdir $BUILD_DIR" \
    --define "_version $VERSION"

# Report results
echo ""
echo "Build completed successfully!"
echo "=========================="

# Find and display the built packages
SRPM_FILE=$(find "$BUILD_DIR/SRPMS" -name "${PACKAGE_NAME}-${VERSION}-*.src.rpm" | head -1)
RPM_FILE=$(find "$BUILD_DIR/RPMS" -name "${PACKAGE_NAME}-${VERSION}-*.rpm" | head -1)

if [ -n "$SRPM_FILE" ]; then
    echo "Source RPM: $SRPM_FILE"
    echo "Size: $(du -h "$SRPM_FILE" | cut -f1)"
fi

if [ -n "$RPM_FILE" ]; then
    echo "Binary RPM: $RPM_FILE"
    echo "Size: $(du -h "$RPM_FILE" | cut -f1)"
    
    # Display package info
    echo ""
    echo "Package Information:"
    echo "==================="
    rpm -qip "$RPM_FILE"
    
    echo ""
    echo "Package Contents:"
    echo "================="
    rpm -qlp "$RPM_FILE" | head -20
    if [ $(rpm -qlp "$RPM_FILE" | wc -l) -gt 20 ]; then
        echo "... and $(( $(rpm -qlp "$RPM_FILE" | wc -l) - 20 )) more files"
    fi
fi

echo ""
echo "Installation Instructions:"
echo "========================="
echo "To install the package:"
echo "  sudo dnf install $RPM_FILE"
echo ""
echo "To install dependencies first:"
echo "  sudo dnf install gtk4 libadwaita python3-gobject python3-dbus python3-requests"
echo ""
echo "After installation, run with:"
echo "  streamcontroller"
echo ""
echo "For USB device access, add your user to the plugdev group:"
echo "  sudo usermod -a -G plugdev \$USER"
echo "  (then log out and back in)"

exit 0

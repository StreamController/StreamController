# StreamController RPM Installation Guide

This guide provides comprehensive instructions for building and installing StreamController as an RPM package on Fedora and other RPM-based Linux distributions.

## Quick Start

For users who just want to install:

```bash
# 1. Install build dependencies
sudo dnf install rpm-build desktop-file-utils python3-devel

# 2. Clone and build
git clone https://github.com/StreamController/StreamController.git
cd StreamController/rpm
make rpm

# 3. Install the package
make install

# 4. Set up USB permissions
sudo usermod -a -G plugdev $USER
# Log out and back in, then run:
streamcontroller
```

## Detailed Installation Process

### Step 1: Install Build Dependencies

#### Fedora / RHEL / CentOS
```bash
sudo dnf install rpm-build desktop-file-utils python3-devel git
```

#### openSUSE
```bash
sudo zypper install rpm-build desktop-file-utils python3-devel git
```

### Step 2: Clone the Repository

```bash
git clone https://github.com/StreamController/StreamController.git
cd StreamController/rpm
```

### Step 3: Build the RPM Package

You have several options for building:

#### Option A: Using Make (Recommended)
```bash
# Build complete RPM package
make rpm

# Or build just the source RPM
make srpm

# Check what will be built
make version-info
```

#### Option B: Using the Build Script Directly
```bash
./build_rpm.sh
```

#### Option C: Manual RPM Build
```bash
# Set up build environment
mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# Create source tarball (from project root)
cd ..
tar --exclude='.git*' --exclude='rpm/' --exclude='flatpak/' \
    -czf ~/rpmbuild/SOURCES/streamcontroller-1.5.2.tar.gz \
    --transform 's,^,streamcontroller-1.5.2/,' .

# Copy spec file and build
cd rpm
cp StreamController.spec ~/rpmbuild/SPECS/
rpmbuild -bb ~/rpmbuild/SPECS/StreamController.spec
```

### Step 4: Install the Package

#### Automatic Installation (with Make)
```bash
make install
```

#### Manual Installation
```bash
# Find the built package
RPM_FILE=$(find ~/rpmbuild/RPMS -name 'streamcontroller-*.rpm' | head -1)

# Install with dependency resolution
sudo dnf install "$RPM_FILE"
```

### Step 5: Post-Installation Setup

#### Configure USB Device Access
```bash
# Add your user to the plugdev group
sudo usermod -a -G plugdev $USER

# Verify the group was added
groups $USER

# Log out and log back in for changes to take effect
```

#### Verify Installation
```bash
# Check if the package is installed
rpm -q streamcontroller

# Check package files
rpm -ql streamcontroller

# Test the application
streamcontroller --help
```

## What Gets Installed

### Application Files
```
/usr/share/streamcontroller/     # Main application directory
├── main.py                     # Application entry point
├── src/                        # Source code modules
├── streamcontroller/           # Core application files
├── Assets/                     # Icons, fonts, images
├── locales/                    # Language files
├── vendor/                     # Bundled Python dependencies
└── requirements.txt            # Dependency list
```

### System Integration
```
/usr/bin/streamcontroller                    # Executable launcher
/usr/share/applications/streamcontroller.desktop  # Desktop entry
/usr/share/icons/hicolor/256x256/apps/streamcontroller.png  # Icon
/etc/udev/rules.d/70-streamcontroller.rules  # USB device rules
```

### Documentation
```
/usr/share/doc/streamcontroller/README.md    # User documentation
/usr/share/licenses/streamcontroller/LICENSE # Software license
```

## Runtime Dependencies

The RPM package automatically handles these dependencies:

### Core System Dependencies
- **GTK4** (>= 4.0) - Modern UI toolkit
- **libadwaita** (>= 1.0) - GNOME design system
- **Python 3.11+** - Runtime environment
- **gobject-introspection** - Python-GTK bindings

### Hardware Support
- **libusb1** - USB device communication
- **hidapi** - HID device support
- **udev** - Device management

### System Integration
- **dbus** - Inter-process communication
- **systemd** - Service management

### Python Modules (Bundled)
The package includes these Python dependencies:
- loguru, requests, pillow, pyyaml
- StreamDeck device libraries
- Cairo graphics libraries
- Various utility modules

## Usage After Installation

### Starting the Application

#### From Desktop Environment
- Find "StreamController" in your application menu
- Click the icon to launch

#### From Command Line
```bash
# Start normally
streamcontroller

# Start with debug output
streamcontroller --debug

# Get help
streamcontroller --help
```

### First-Time Setup

1. **Connect your Stream Deck** device via USB
2. **Grant permissions** when prompted
3. **Follow the onboarding** process in the application
4. **Download plugins** from the built-in store

### Troubleshooting Common Issues

#### Device Not Recognized
```bash
# Check if device is detected by system
lsusb | grep -i elgato

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger --subsystem-match=usb

# Check user permissions
groups $USER | grep plugdev
```

#### Application Won't Start
```bash
# Check for missing dependencies
ldd /usr/bin/streamcontroller

# Run with verbose output
streamcontroller --debug

# Check system logs
journalctl -u streamcontroller --since "1 hour ago"
```

#### Permission Errors
```bash
# Verify udev rules are installed
ls -la /etc/udev/rules.d/70-streamcontroller.rules

# Check file permissions
ls -la /usr/share/streamcontroller/

# Re-add user to group
sudo usermod -a -G plugdev $USER
```

## Package Management

### Updating StreamController

#### Method 1: Rebuild and Reinstall
```bash
cd StreamController/rpm
git pull origin main
make clean
make rpm
make install
```

#### Method 2: Manual Package Update
```bash
# Remove old version
sudo dnf remove streamcontroller

# Install new version
sudo dnf install ./new-streamcontroller-package.rpm
```

### Uninstalling

```bash
# Remove the package
sudo dnf remove streamcontroller

# Remove user from plugdev group (optional)
sudo gpasswd -d $USER plugdev

# Remove user data (optional)
rm -rf ~/.config/streamcontroller
rm -rf ~/.local/share/streamcontroller
```

## Advanced Configuration

### Custom Installation Paths

You can modify the spec file to change installation paths:

```spec
# Custom application directory
%define appdir /opt/streamcontroller

# Custom data directory  
%define datadir /var/lib/streamcontroller
```

### Building for Different Architectures

```bash
# Build for specific architecture
rpmbuild --target x86_64 -bb StreamController.spec

# Build for multiple architectures
for arch in x86_64 aarch64; do
    rpmbuild --target $arch -bb StreamController.spec
done
```

### Creating a Repository

```bash
# Create repository structure
mkdir -p repo/{x86_64,SRPMS}
cp ~/rpmbuild/RPMS/noarch/*.rpm repo/x86_64/
cp ~/rpmbuild/SRPMS/*.rpm repo/SRPMS/

# Create repository metadata
createrepo repo/x86_64
createrepo repo/SRPMS

# Serve repository
cd repo && python3 -m http.server 8000
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Build RPM
on: [push, pull_request]

jobs:
  build-rpm:
    runs-on: ubuntu-latest
    container: fedora:latest
    steps:
      - uses: actions/checkout@v3
      - name: Install dependencies
        run: dnf install -y rpm-build desktop-file-utils python3-devel
      - name: Build RPM
        run: make rpm
      - name: Upload artifacts
        uses: actions/upload-artifact@v3
        with:
          name: rpm-packages
          path: ~/rpmbuild/RPMS/
```

### Local Testing with Containers

```bash
# Test on Fedora
podman run -it --rm -v .:/src fedora:latest bash
cd /src
dnf install -y rpm-build desktop-file-utils python3-devel
make rpm

# Test installation
dnf install -y ~/rpmbuild/RPMS/noarch/streamcontroller-*.rpm
streamcontroller --version
```

## Support and Contributing

### Getting Help

1. **Check the documentation** in `/usr/share/doc/streamcontroller/`
2. **Review build logs** for specific error messages
3. **Open an issue** on the GitHub repository
4. **Join the Discord** server for community support

### Contributing to Packaging

1. **Test on multiple distributions** (Fedora, RHEL, openSUSE)
2. **Follow packaging guidelines** for target distributions
3. **Update documentation** when making changes
4. **Validate with tools** like rpmlint before submitting

### Distribution-Specific Guidelines

- **Fedora**: [Fedora Packaging Guidelines](https://docs.fedoraproject.org/en-US/packaging-guidelines/)
- **RHEL/CentOS**: [EPEL Packaging Guidelines](https://fedoraproject.org/wiki/EPEL/GuidelinesAndPolicies)
- **openSUSE**: [openSUSE Packaging Guidelines](https://en.opensuse.org/openSUSE:Packaging_guidelines)

The RPM packaging provides a robust, native installation method that integrates seamlessly with your system's package management while maintaining all of StreamController's functionality.

# StreamController RPM Packaging

This directory contains the RPM packaging files for StreamController, enabling easy installation on Fedora, RHEL, CentOS, openSUSE, and other RPM-based Linux distributions.

## Overview

StreamController is packaged as a native RPM with proper dependency management, system integration, and follows Fedora packaging guidelines. The package includes:

- Complete application files
- Desktop integration with .desktop file and icons
- udev rules for Stream Deck device access
- Proper permission handling and user group management
- System dependency declarations for automatic resolution

## What the RPM Package Does

### 1. **Application Installation**
- Installs StreamController to `/usr/share/streamcontroller/`
- Creates executable wrapper script in `/usr/bin/streamcontroller`
- Bundles required Python dependencies in vendor directory
- Sets up proper Python path and environment

### 2. **System Integration**
- Installs desktop file for application launcher integration
- Adds application icon to system icon cache
- Integrates with desktop environments (GNOME, KDE, etc.)
- Provides proper application metadata

### 3. **Hardware Access Setup**
- Installs udev rules for Stream Deck device recognition
- Configures USB device permissions
- Provides instructions for user group membership

### 4. **Dependency Management**
- Declares system dependencies (GTK4, libadwaita, Python modules)
- Bundles Python package dependencies not available as RPMs
- Ensures compatibility across different RPM distributions

### 5. **Post-Installation Configuration**
- Updates system icon cache
- Reloads udev rules for immediate device recognition
- Provides user guidance for USB access permissions

## Package Architecture

### Directory Structure
```
/usr/share/streamcontroller/          # Main application directory
├── main.py                          # Application entry point
├── src/                             # Source code
├── streamcontroller/                # Core modules
├── Assets/                          # Icons, images, fonts
├── locales/                         # Internationalization
├── vendor/                          # Bundled Python dependencies
│   └── lib/python3.x/site-packages/
└── requirements.txt                 # Original dependency list

/usr/bin/streamcontroller            # Executable wrapper script
/usr/share/applications/streamcontroller.desktop  # Desktop integration
/usr/share/icons/hicolor/256x256/apps/streamcontroller.png  # Application icon
/etc/udev/rules.d/70-streamcontroller.rules  # USB device rules
```

### Why This Architecture?

1. **FHS Compliance**: Follows Filesystem Hierarchy Standard
2. **Vendor Dependencies**: Bundles Python packages not available as RPMs
3. **Isolation**: Keeps application files separate from system files
4. **Flexibility**: Allows easy updates and maintenance

## Building the RPM

### Prerequisites

Install required build tools:
```bash
# Fedora/RHEL/CentOS
sudo dnf install rpm-build desktop-file-utils python3-devel

# openSUSE
sudo zypper install rpm-build desktop-file-utils python3-devel
```

### Build Process

1. **Clone the repository:**
   ```bash
   git clone https://github.com/StreamController/StreamController.git
   cd StreamController/rpm
   ```

2. **Run the build script:**
   ```bash
   # Using the Makefile (recommended)
   make rpm

   # Or using the build script directly
   ./build_rpm.sh
   ```

3. **Built packages will be in:**
   ```
   ~/rpmbuild/RPMS/noarch/streamcontroller-*.rpm     # Binary package
   ~/rpmbuild/SRPMS/streamcontroller-*.src.rpm       # Source package
   ```

### Build Script Features

The `build_rpm.sh` script:
- **Validates prerequisites** - Checks for required tools
- **Creates source tarball** - Packages source code properly
- **Manages versions** - Extracts version from spec file
- **Builds both packages** - Creates source and binary RPMs
- **Provides feedback** - Shows package info and installation instructions
- **Error handling** - Exits cleanly on failures

## Installation

### From Built Package
```bash
# Install the package
sudo dnf install ~/rpmbuild/RPMS/noarch/streamcontroller-*.rpm

# Or with dependencies resolved automatically
sudo dnf install ./streamcontroller-*.rpm
```

### Dependencies

The package automatically handles these dependencies:

**System Dependencies:**
- GTK4 and libadwaita for UI
- Python 3.11+ with GObject bindings
- D-Bus for system integration
- USB libraries for device communication

**Python Dependencies (bundled):**
- loguru, requests, pillow, pyyaml
- StreamDeck libraries and device drivers
- Various utility and UI libraries

### Post-Installation Setup

1. **USB Device Access Setup:**
   
   StreamController needs USB access to communicate with Stream Deck devices. The RPM package automatically creates a `plugdev` group if it doesn't exist and provides setup instructions.

   **Option A: Using plugdev group (recommended):**
   ```bash
   # Add your user to the plugdev group
   sudo usermod -a -G plugdev $USER
   
   # Log out and back in for changes to take effect
   ```

   **Option B: Alternative methods if plugdev doesn't work:**
   ```bash
   # Method 1: Create and use a custom group
   sudo groupadd streamdeck-users
   sudo usermod -a -G streamdeck-users $USER
   # Then modify udev rules to use this group
   
   # Method 2: Use existing wheel group (if user is admin)
   # No additional setup needed if user is already in wheel group
   
   # Method 3: Use systemd-udev rules (modern approach)
   # Uses ACL permissions instead of groups
   ```

2. **Install Python dependencies:**
   ```bash
   pip3 install --user -r /usr/share/streamcontroller/requirements.txt
   ```

3. **Connect your Stream Deck** and launch the application:
   ```bash
   streamcontroller
   ```

4. **Verify USB access:**
   ```bash
   # Check if Stream Deck is detected
   lsusb | grep -i elgato
   
   # Check device permissions
   ls -la /dev/bus/usb/*/
   ```

## Why RPM Packaging?

### Advantages of This Approach

1. **Native Integration**
   - Proper dependency resolution
   - System service integration
   - Standard installation/removal process

2. **Distribution Compatibility**
   - Works across RPM-based distributions
   - Follows packaging standards
   - Easy to maintain and update

3. **Offline Installation**
   - Bundles Python dependencies
   - No internet required after download
   - Reproducible installations

4. **Security and Trust**
   - Package verification through RPM signatures
   - Clear ownership and permissions
   - Audit trail for installations

### Comparison with Other Installation Methods

| Method | Pros | Cons |
|--------|------|------|
| **RPM Package** | Native integration, dependency management, offline install | Distribution-specific |
| **Flatpak** | Universal, sandboxed, automatic updates | Large size, limited system access |
| **Source Install** | Latest features, customizable | Complex dependencies, manual updates |
| **pip/PyPI** | Easy for Python users | System conflicts, no system integration |

## Maintaining the Package

### Updating Version

1. Edit `StreamController.spec`:
   ```spec
   Version:        1.6.0
   Release:        1%{?dist}
   ```

2. Add changelog entry:
   ```spec
   %changelog
   * Mon Jul 01 2025 StreamController Team <dev@streamcontroller.org> - 1.6.0-1
   - Updated to version 1.6.0
   - Added new plugin features
   - Fixed USB communication issues
   ```

3. Rebuild package:
   ```bash
   ./build_rpm.sh
   ```

### Adding Dependencies

Edit the spec file to add new requirements:
```spec
# For system packages
Requires:       new-system-package

# For Python packages (add to requirements.txt instead)
```

### Debugging Package Issues

1. **Validate spec file:**
   ```bash
   rpmlint StreamController.spec
   ```

2. **Check package contents:**
   ```bash
   rpm -qlp streamcontroller-*.rpm
   ```

3. **Verify dependencies:**
   ```bash
   rpm -qRp streamcontroller-*.rpm
   ```

4. **Test installation in clean environment:**
   ```bash
   # Use podman/docker for testing
   podman run -it fedora:latest
   dnf install -y ./streamcontroller-*.rpm
   ```

## Troubleshooting

### Common Build Issues

1. **Missing build dependencies:**
   ```bash
   sudo dnf builddep StreamController.spec
   ```

2. **Python dependency conflicts:**
   - Check requirements.txt for conflicting versions
   - Update spec file dependency versions

3. **File conflicts:**
   - Ensure files don't conflict with other packages
   - Use proper file ownership and permissions

### Common Installation Issues

1. **USB device not recognized:**
   ```bash
   # Check if udev rules are loaded
   sudo udevadm control --reload-rules
   sudo udevadm trigger --subsystem-match=usb
   
   # Verify Stream Deck is detected
   lsusb | grep -i elgato
   ```

2. **Permission denied errors:**
   ```bash
   # Verify user is in plugdev group
   groups $USER
   
   # If plugdev group doesn't exist, create it
   sudo groupadd plugdev
   sudo usermod -a -G plugdev $USER
   
   # Alternative: Use ACL permissions for specific device
   # Find your device first
   lsusb | grep -i elgato
   # Then set ACL (replace XXX:YYY with bus:device from lsusb)
   sudo setfacl -m u:$USER:rw /dev/bus/usb/XXX/YYY
   ```

3. **Missing dependencies:**
   ```bash
   # Check for missing system packages
   dnf check streamcontroller
   
   # Install missing Python dependencies
   pip3 install --user -r /usr/share/streamcontroller/requirements.txt
   ```

4. **Application won't start:**
   ```bash
   # Check logs for errors
   journalctl --user -u streamcontroller
   
   # Or check application logs (after first run)
   ls ~/.var/app/com.core447.StreamController/data/logs/
   ```

## Configuration

StreamController stores its configuration in the following locations:

### Configuration Files

- **Main settings:** `~/.var/app/com.core447.StreamController/data/settings/settings.json`
- **Static settings:** `~/.var/app/com.core447.StreamController/static/settings.json`
- **Plugin settings:** `~/.var/app/com.core447.StreamController/data/settings/plugins/[plugin-id]/settings.json`

### Data Directories

- **Application data:** `~/.var/app/com.core447.StreamController/data/`
- **Page configurations:** `~/.var/app/com.core447.StreamController/data/pages/`
- **Plugin files:** `~/.var/app/com.core447.StreamController/data/plugins/`
- **Log files:** `~/.var/app/com.core447.StreamController/data/logs/`
- **Cache files:** `~/.var/app/com.core447.StreamController/data/cache/`

### Customizing Data Path

You can change the data directory by creating a static settings file:

```bash
# Create the static settings directory
mkdir -p ~/.var/app/com.core447.StreamController/static/

# Create settings file with custom data path
cat > ~/.var/app/com.core447.StreamController/static/settings.json << 'EOF'
{
    "data-path": "/path/to/your/custom/data/directory"
}
EOF
```

Note: The application uses Flatpak-style directory structure (`~/.var/app/com.core447.StreamController/`) even when installed via RPM, which provides consistency across installation methods.

## Contributing

When contributing to the RPM packaging:

1. **Test on multiple distributions** (Fedora, RHEL, openSUSE)
2. **Follow packaging guidelines** for your target distribution
3. **Update documentation** when making changes
4. **Validate with rpmlint** before submitting

## Distribution-Specific Notes

### Fedora
- Uses latest GTK4 and libadwaita versions
- Active Python ecosystem with many packaged modules
- Fastest adoption of new technologies

### RHEL/CentOS
- More conservative dependency versions
- May need additional repositories for some dependencies
- Focus on stability over latest features

### openSUSE
- Different package names for some dependencies
- May require spec file adjustments for compatibility
- Strong RPM packaging tradition

## Support

For RPM packaging issues:
1. Check this README for common solutions
2. Open an issue on the StreamController GitHub repository
3. Join the Discord server for community support
4. Review the build logs for specific error messages

The RPM packaging aims to provide a seamless, native installation experience while maintaining the full functionality of StreamController.

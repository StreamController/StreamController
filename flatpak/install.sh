#!/bin/sh

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check if flatpak-builder is installed
if ! command_exists flatpak-builder; then
    echo "Error: flatpak-builder is not installed."
    echo "Please install flatpak-builder and rerun the script."
    exit 1
fi

# Check if StreamController directory exists
if [ -d "StreamController" ]; then
    echo "Warning: The directory 'StreamController' already exists."
    read -p "Do you want to continue? (y/n): " choice
    case "$choice" in 
        y|Y ) echo "Continuing...";;
        n|N ) echo "Aborting."; exit 1;;
        * ) echo "Invalid input. Aborting."; exit 1;;
    esac
fi

# Check if com.core447.StreamController is installed
if flatpak list | grep -q "com.core447.StreamController"; then
    echo "Warning: com.core447.StreamController is already installed."
    echo "The data should persist."
    read -p "Do you want to remove it before continuing? (y/n): " choice
    case "$choice" in 
        y|Y )
            echo "Removing com.core447.StreamController..."
            flatpak uninstall com.core447.StreamController -y
            ;;
        n|N )
            echo "Continuing without removing the existing installation..."
            ;;
        * )
            echo "Invalid input. Aborting."
            exit 1
            ;;
    esac
fi

# Create StreamController directory and navigate into it
mkdir -p StreamController
cd StreamController

# Download necessary files
wget https://raw.githubusercontent.com/StreamController/StreamController/dev/com.core447.StreamController.yml
wget https://raw.githubusercontent.com/StreamController/StreamController/dev/pypi-requirements.yaml

# Install necessary Flatpak runtimes
flatpak install runtime/org.gnome.Sdk//46 --system -y
flatpak install runtime/org.gnome.Platform//46 --system -y

# Build and install StreamController
flatpak-builder --repo=repo --force-clean --install --user build-dir com.core447.StreamController.yml

#!/bin/sh

# Installs StreamController as a flatpak

mkdir StreamController
cd StreamController

wget https://raw.githubusercontent.com/StreamController/StreamController/dev/com.core447.StreamController.yml
wget https://raw.githubusercontent.com/StreamController/StreamController/dev/pypi-requirements.yaml

flatpak-builder --repo=repo --force-clean --install --user build-dir com.core447.StreamController.yml
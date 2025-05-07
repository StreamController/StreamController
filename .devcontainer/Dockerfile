FROM ubuntu:24.04

# Define Python version as build argument with default
ARG PYTHON_VERSION=3.12

# Prevent interactive prompts during apt installation
ENV DEBIAN_FRONTEND=noninteractive

# Install minimal system requirements and fix GObject Introspection issues
RUN apt-get update && apt-get install -y \
    curl git build-essential cmake pkg-config \
    libgtk-4-dev libadwaita-1-dev \
    libdbus-1-dev dbus dbus-x11 \
    python3-gi python3-gi-cairo python3-dev python3-dbus \
    gobject-introspection libgirepository-2.0-dev \
    libgirepository1.0-dev \
    gir1.2-gtk-4.0 gir1.2-adw-1 gir1.2-glib-2.0 \
    libportal-dev gir1.2-xdp-1.0 libhidapi-libusb0 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*


# create the dbus socket location and spawn dbus in the postcreate
RUN mkdir -p /run/user/1000 && chown 1000:1000 /run/user/1000 && chmod 700 /run/user/1000
USER ubuntu
WORKDIR /app

# Install uv
ENV PATH="/app/.venv/bin:/home/ubuntu/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
RUN curl -LsSf https://astral.sh/uv/install.sh | bash

# Use uv to install Python and create virtual environment
RUN uv python install ${PYTHON_VERSION} && \
    uv venv -p ${PYTHON_VERSION} .venv && \
    echo 'export PATH="/app/.venv/bin:$PATH"' >> ~/.bashrc

CMD ["/bin/bash"] 
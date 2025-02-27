#!/bin/bash
#
# Create a flatpak of StreamController and optionally a flatpak bundle
#

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -h --help             Show this message"
    echo "  --repo=path           Path to StreamController repo (must be local)"
    echo "                        use 'current' for git repo in current pwd"
    echo "  --branch=branch       Name of branch in --repo to use"
    echo "                        Ignored if --repo is not specified"
    echo "  --make-bundle         Create a flatpak bundle so you can try"
    echo "                        it on another system"
    echo "  --yes                 Answer yes to all questions"
}

askyesno() {
    local msg="$1"
    local ans

    # Handle --yes command line argument
    if (( $yes == 1 )); then
        return 0
    fi

    while true; do
        read -p "$msg [y/n]: " ans
        if [[ $ans == y* ]]; then
            return 0
        elif [[ $ans == n* ]]; then
            return 1
        fi
    done
}

# Handle command line arguments
args=$(getopt -o h --long help,repo:,branch:,make-bundle,yes -n $(basename $0) -- "$@")
if (( $? != 0 )); then
    exit 1
fi

eval set -- "$args"

unset -v repo
unset -v branch
make_bundle=0
yes=0
while : ; do
    case "$1" in
        -h|--help)
            usage
            exit 0
            ;;
        --repo)
            repo="$2"
            shift
            ;;
        --branch)
            branch="$2"
            shift
            ;;
        --make-bundle)
            make_bundle=1
            ;;
        --yes)
            yes=1
            ;;
        --)
            shift
            break
            ;;
        *)
            echo "Internal error ($1)"
            exit 1
            ;;
    esac
    shift
done

case "$repo" in
    "current")
        # Special name: use git repo we are currently in
        if git rev-parse --git-dir > /dev/null 2>&1; then
            repo=$(git rev-parse --show-toplevel)
        else
            echo "Not in a git repository"
            exit 1
        fi
        ;;
    file://*)
        # Remove file:// prefix
        repo=${repo#file://};;
    "")
        # No repo specified, we'll use official location
        ;;
    /*)
        # Absolute path
        ;;
    *)
        # Convert relative path to absolute
        repo=$(realpath $repo);;
esac

if [[ ! -z "$repo" ]]; then
    if [[ ! -d $repo || ! -d $repo/.git ]]; then
        echo "Error: repository $repo does not exist or is not a git repo"
        exit 1
    fi

    if [[ -z $branch ]]; then
        echo "branch not specified.  Using branch from repo's HEAD"
        branch=$(git --git-dir=$repo/.git rev-parse --abbrev-ref HEAD)
    fi
fi


# Check if flatpak-builder is installed
if ! command_exists flatpak-builder; then
    echo "Error: flatpak-builder is not installed."
    echo "Please install flatpak-builder and rerun the script."
    exit 1
fi

# Check if StreamController directory exists
if [[ -d "StreamController" ]]; then
    echo "Warning: The directory 'StreamController' already exists."
    askyesno "Do you want to continue?" || exit 1
fi

# Check if com.core447.StreamController is installed
if flatpak list | grep -q "com.core447.StreamController"; then
    echo "Warning: com.core447.StreamController is already installed."
    echo "The data should persist."
    if askyesno "Do you want to remove it before continuing?"; then
        echo "Removing com.core447.StreamController..."
        flatpak uninstall com.core447.StreamController -y
    fi
fi

# Create StreamController directory and navigate into it
mkdir -p StreamController
cd StreamController || exit 1

if [[ -z $repo ]]; then
    # Download necessary files
    echo "Downloading com.core447.StreamController.yml"
    wget -O com.core447.StreamController.yml https://raw.githubusercontent.com/StreamController/StreamController/main/com.core447.StreamController.yml
    echo "Downloading pypi-requirements.yaml"
    wget -O pypi-requirements.yaml https://raw.githubusercontent.com/StreamController/StreamController/main/pypi-requirements.yaml
else
    echo "Copying com.core447.StreamController.yml"
    cp $repo/com.core447.StreamController.yml .

    echo "Copying pypi-requirements.yaml"
    cp $repo/pypi-requirements.yaml .

    # Get yq so we can edit the .yml file with the location
    # of the git repo and branch we want to use
    #
    # Don't use the command_exists function and ask user to install package
    # if it is missing.  There are two very incompatible version of yq out
    # there and it is very likely they either have or would install the
    # wrong one.
    echo "Downloading yq"
    wget --quiet https://github.com/mikefarah/yq/releases/download/v4.44.3/yq_linux_amd64 -O yq
    chmod +x yq

    echo "Editing com.core447.StreamController.yml"
    # Find the StreamController section and replace the
    # url and branch fields under the first (only) sources sub-section.
    # Environment variables are used to pass values to yq.
    # Note:
    REPO="file://$repo" BRANCH="$branch" ./yq -i '
        with(.modules[] | select(.name == "StreamController").sources[0];
             .url = strenv(REPO) |
             .branch = strenv(BRANCH))' com.core447.StreamController.yml

fi


if [[ -d shared-modules ]]; then
    echo "Updating flathub shared-modules"
    git --work-tree=shared-modules --git-dir=shared-modules/.git fetch
else
    echo "Downloading flathub shared-modules"
    git clone https://github.com/flathub/shared-modules/ shared-modules
fi

# Install necessary Flatpak runtimes
echo "Installing flathub runtimes"
flatpak install runtime/org.gnome.Sdk//46 --system -y
flatpak install runtime/org.gnome.Platform//46 --system -y

# Build and install StreamController
echo "Building flatpak (this will take a while)"
flatpak-builder --repo=repo --force-clean --install --user build-dir com.core447.StreamController.yml
rc=$?
if (( $rc != 0 )); then
    exit $rc
fi

if (( $make_bundle == 1 )); then
    echo "Creating flatpak bundle (StreamController.flatpak)"
    flatpak build-bundle repo StreamController.flatpak com.core447.StreamController
fi


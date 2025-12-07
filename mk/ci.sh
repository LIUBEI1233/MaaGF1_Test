#!/bin/bash

# -----------------------------------------------------------------------------
# MaaGFL CI Helper Script
# -----------------------------------------------------------------------------
# Usage: bash mk/ci.sh <command>
# Commands:
#   set_tag      - Calculate version tag and release status
#   get_deps     - Read config and fetch MFAAvalonia release info
#   summary      - Generate GitHub Actions step summary
#   zip_assets   - Zip artifacts for release
# -----------------------------------------------------------------------------

set -e # Exit on error

# Helper function to write to GITHUB_OUTPUT
output() {
    echo "$1=$2" >> "$GITHUB_OUTPUT"
}

case "$1" in
    "set_tag")
        # Requires env: GITHUB_REF, GITHUB_REPOSITORY, GITHUB_TOKEN
        echo "Calculating tag info..."
        
        if [[ "$GITHUB_REF" == "refs/tags/v"* ]]; then
            is_release="true"
        else
            is_release="false"
        fi

        tag=$(git describe --tags --match "v*" "$GITHUB_REF" 2>/dev/null || true)

        if [[ "$tag" != v* ]]; then
            echo "No local tag found, fetching latest from API..."
            tag=$(curl -sX GET "https://api.github.com/repos/$GITHUB_REPOSITORY/releases/latest" \
                --header "authorization: Bearer $GITHUB_TOKEN" | \
                awk '/tag_name/{print $4}' FS='["]')
            
            if [[ "$tag" != v* ]]; then
                tag="v0.0.0"
            fi
            tag=$(date "+$tag-%y%m%d-$(git rev-parse --short HEAD)")
        fi

        if [[ "$is_release" == "false" ]]; then
            prefix=${tag%-*-*}
            suffix=${tag#$prefix-}
            tag="$prefix-ci.$suffix"
        fi

        echo "Result: tag=$tag, is_release=$is_release"
        output "tag" "$tag"
        output "is_release" "$is_release"
        ;;

    "get_deps")
        # Requires env: GITHUB_TOKEN
        echo "Reading configuration..."
        
        repo=$(python -c "import configparser; c = configparser.ConfigParser(); c.read('mk/.conf'); print(c['install']['mfa_repo'])")
        tag_conf=$(python -c "import configparser; c = configparser.ConfigParser(); c.read('mk/.conf'); print(c['install']['mfa_tag'])")
        
        output "mfa_repo" "$repo"
        output "config_mfa_tag" "$tag_conf" 

        echo "Configuration Loaded: Repo=$repo, Tag=$tag_conf"
        echo "Fetching release info..."

        if [ "$tag_conf" == "latest" ]; then
            API_URL="https://api.github.com/repos/$repo/releases/latest"
        else
            API_URL="https://api.github.com/repos/$repo/releases/tags/$tag_conf"
        fi

        response=$(curl -sX GET "$API_URL" --header "authorization: Bearer $GITHUB_TOKEN")

        if echo "$response" | jq -e .message > /dev/null; then
             echo "Error fetching release info: $(echo "$response" | jq -r .message)"
        fi

        tag_name=$(echo "$response" | jq -r '.tag_name // "unknown"')
        date=$(echo "$response" | jq -r '.published_at // "unknown"')
        url=$(echo "$response" | jq -r '.html_url // "unknown"')
        prerelease=$(echo "$response" | jq -r '.prerelease // false')

        [[ "$tag_name" == "unknown" ]] && tag_name="No releases"
        [[ "$date" == "unknown" ]] && date="N/A"
        [[ "$url" == "unknown" ]] && url=""

        echo "MFAAvalonia Info: Tag=$tag_name, Date=$date"

        output "mfa_tag" "$tag_name"
        output "mfa_date" "$date"
        output "mfa_url" "$url"
        output "mfa_prerelease" "$prerelease"
        ;;

    "summary")
        # Requires env: TAG, IS_RELEASE, STATUS_INSTALL
        BUILD_DATE=$(date -u '+%Y-%m-%d %H:%M:%S UTC')
        
        if [[ "$STATUS_INSTALL" == *"success"* ]]; then
            STATUS_TEXT="[SUCCESS]"
        else
            STATUS_TEXT="[FAILED]"
        fi
        
        cat >> $GITHUB_STEP_SUMMARY << EOF
# Overall Build Summary

## Build Results
| Architecture | Status | 
|--------------|--------|
| **aarch64** | ${STATUS_TEXT} |
| **x86_64** | ${STATUS_TEXT} |

## Info
- **Tag:** \`${TAG}\`
- **Release:** $( [[ "$IS_RELEASE" == "true" ]] && echo '[YES]' || echo '[NO]' )
- **Date:** ${BUILD_DATE}

$( [[ "$IS_RELEASE" == "true" ]] && echo '## Release Build' || echo '## CI Build' )

---
EOF
        ;;

    "zip_assets")
        # Requires env: TAG
        echo "Starting zip_assets..."
        
        if [ -z "$TAG" ]; then
            echo "Error: TAG environment variable is not set."
            exit 1
        fi

        if [ ! -d "assets" ]; then
            echo "Error: 'assets' directory not found."
            exit 1
        fi

        cd assets
        shopt -s nullglob
        
        for f in *; do
            if [ -d "$f" ]; then
                # Only process folders starting with MaaGF1-GUI
                if [[ "$f" != "MaaGF1-GUI"* ]]; then
                    echo "Skipping non-GUI artifact: $f"
                    continue
                fi

                echo "Processing artifact: $f"
                
                if [ -z "$(ls -A "$f")" ]; then
                    echo "Warning: Directory '$f' is empty. Skipping."
                    continue
                fi

                # The folder name ($f) already contains the TAG (from YAML upload-artifact).
                (
                    cd "$f"
                    echo "Zipping content of $f to ../$f.zip"
                    zip -r "../$f.zip" .
                )
            else
                echo "Skipping non-directory: $f"
            fi
        done
        ;;
    
    "release_summary")
        # Requires env: TAG
        cat >> $GITHUB_STEP_SUMMARY << EOF
# Release Published!
Release Tag: \`${TAG}\`
EOF
        ;;

    *)
        echo "Unknown command: $1"
        exit 1
        ;;
esac
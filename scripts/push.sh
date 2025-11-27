#!/bin/bash
set -e

# Load environment variables from .env file if it exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
if [ -f "${PROJECT_ROOT}/.env" ]; then
    set -a
    source "${PROJECT_ROOT}/.env"
    set +a
fi

# Push script for recipe-helper Docker image
# Usage: ./push.sh [local|ghcr|both]
#   local: Push to local registry (localhost:5000)
#   ghcr: Push to GitHub Container Registry (requires GITHUB_TOKEN)
#   both: Push to both registries (default)

REGISTRY_TARGET="${1:-both}"
PROJECT_NAME="recipe-helper"
LOCAL_REGISTRY="localhost:5000"
GHCR_REGISTRY="ghcr.io"

# Get git commit SHA for versioning (if available)
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "dev")
VERSION_TAG="${GIT_SHA}"

echo "Pushing ${PROJECT_NAME} image..."
echo "Registry target: ${REGISTRY_TARGET}"
echo "Version tag: ${VERSION_TAG}"

# Push to local registry
if [ "${REGISTRY_TARGET}" = "local" ] || [ "${REGISTRY_TARGET}" = "both" ]; then
    echo "Pushing to local registry (${LOCAL_REGISTRY})..."
    
    # Check if local registry is accessible
    if ! docker pull ${LOCAL_REGISTRY}/alpine:latest 2>/dev/null && ! curl -s http://${LOCAL_REGISTRY}/v2/ > /dev/null 2>&1; then
        echo "Warning: Local registry at ${LOCAL_REGISTRY} may not be running."
        echo "Start it with: docker compose -f ../../docker/registry/docker-compose.yml up -d"
        read -p "Continue anyway? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    docker push ${LOCAL_REGISTRY}/${PROJECT_NAME}:${VERSION_TAG}
    docker push ${LOCAL_REGISTRY}/${PROJECT_NAME}:latest
    echo "✓ Pushed to local registry"
fi

# Push to GitHub Container Registry
if [ "${REGISTRY_TARGET}" = "ghcr" ] || [ "${REGISTRY_TARGET}" = "both" ]; then
    echo "Pushing to GitHub Container Registry..."
    
    # Get GitHub username/repo
    if [ -n "${GITHUB_REPOSITORY}" ]; then
        GHCR_IMAGE="${GHCR_REGISTRY}/${GITHUB_REPOSITORY}/${PROJECT_NAME}"
    else
        GIT_REMOTE=$(git remote get-url origin 2>/dev/null | sed 's/.*github.com[:/]\([^.]*\).*/\1/' || echo "")
        if [ -n "${GIT_REMOTE}" ]; then
            GHCR_IMAGE="${GHCR_REGISTRY}/${GIT_REMOTE}/${PROJECT_NAME}"
        else
            echo "Error: Could not determine GitHub repository."
            echo "Set GITHUB_REPOSITORY environment variable or ensure git remote is configured."
            exit 1
        fi
    fi
    
    # Check for authentication token
    if [ -z "${GITHUB_TOKEN}" ]; then
        echo "Error: GITHUB_TOKEN environment variable is required for GHCR push."
        echo ""
        echo "Set GITHUB_TOKEN in your .env file or export it:"
        echo "  export GITHUB_TOKEN=ghp_your_token_here"
        echo ""
        echo "Or run the script with the variable inline:"
        echo "  GITHUB_TOKEN=ghp_your_token_here ./push.sh ghcr"
        echo ""
        echo "Create a personal access token with 'write:packages' permission at:"
        echo "https://github.com/settings/tokens"
        exit 1
    fi
    
    # Login to GHCR
    echo "${GITHUB_TOKEN}" | docker login ${GHCR_REGISTRY} -u "${GITHUB_ACTOR:-$(git config user.name)}" --password-stdin
    
    docker push ${GHCR_IMAGE}:${VERSION_TAG}
    docker push ${GHCR_IMAGE}:latest
    echo "✓ Pushed to GitHub Container Registry"
fi

echo ""
echo "Push complete!"



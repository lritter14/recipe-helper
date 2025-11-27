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

# Build script for recipe-helper Docker image
# Usage: ./build.sh [local|ghcr|both]
#   local: Build and tag for local registry (localhost:5000)
#   ghcr: Build and tag for GitHub Container Registry
#   both: Build and tag for both registries (default)

REGISTRY_TARGET="${1:-both}"
PROJECT_NAME="recipe-helper"
LOCAL_REGISTRY="localhost:5000"
GHCR_REGISTRY="ghcr.io"

# Get git commit SHA for versioning (if available)
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "dev")
VERSION_TAG="${GIT_SHA}"

echo "Building ${PROJECT_NAME} image..."
echo "Registry target: ${REGISTRY_TARGET}"
echo "Version tag: ${VERSION_TAG}"

# Build the base image
docker build -t ${PROJECT_NAME}:${VERSION_TAG} .
docker tag ${PROJECT_NAME}:${VERSION_TAG} ${PROJECT_NAME}:latest

# Tag for local registry
if [ "${REGISTRY_TARGET}" = "local" ] || [ "${REGISTRY_TARGET}" = "both" ]; then
    echo "Tagging for local registry..."
    docker tag ${PROJECT_NAME}:${VERSION_TAG} ${LOCAL_REGISTRY}/${PROJECT_NAME}:${VERSION_TAG}
    docker tag ${PROJECT_NAME}:${VERSION_TAG} ${LOCAL_REGISTRY}/${PROJECT_NAME}:latest
    echo "Local registry tags:"
    echo "  - ${LOCAL_REGISTRY}/${PROJECT_NAME}:${VERSION_TAG}"
    echo "  - ${LOCAL_REGISTRY}/${PROJECT_NAME}:latest"
fi

# Tag for GitHub Container Registry
if [ "${REGISTRY_TARGET}" = "ghcr" ] || [ "${REGISTRY_TARGET}" = "both" ]; then
    # Get GitHub username/repo from git remote or use default
    if [ -n "${GITHUB_REPOSITORY}" ]; then
        GHCR_IMAGE="${GHCR_REGISTRY}/${GITHUB_REPOSITORY}/${PROJECT_NAME}"
    else
        # Try to extract from git remote
        GIT_REMOTE=$(git remote get-url origin 2>/dev/null | sed 's/.*github.com[:/]\([^.]*\).*/\1/' || echo "")
        if [ -n "${GIT_REMOTE}" ]; then
            GHCR_IMAGE="${GHCR_REGISTRY}/${GIT_REMOTE}/${PROJECT_NAME}"
        else
            echo "Warning: Could not determine GitHub repository. Using default format."
            echo "Set GITHUB_REPOSITORY environment variable or ensure git remote is configured."
            GHCR_IMAGE="${GHCR_REGISTRY}/user/${PROJECT_NAME}"
        fi
    fi
    
    echo "Tagging for GitHub Container Registry..."
    docker tag ${PROJECT_NAME}:${VERSION_TAG} ${GHCR_IMAGE}:${VERSION_TAG}
    docker tag ${PROJECT_NAME}:${VERSION_TAG} ${GHCR_IMAGE}:latest
    echo "GHCR tags:"
    echo "  - ${GHCR_IMAGE}:${VERSION_TAG}"
    echo "  - ${GHCR_IMAGE}:latest"
fi

echo ""
echo "Build complete! Use ./push.sh to push images to registries."



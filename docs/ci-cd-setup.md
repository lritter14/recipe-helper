# CI/CD Setup and GitOps Practices

This document explains the CI/CD pipeline, GitOps practices, and how to set up automated testing, building, and deployment.

## Overview

The project uses GitHub Actions for CI/CD, pre-commit hooks for local quality checks, and Watchtower for automatic container updates. The pipeline ensures code quality through automated testing and linting, and automatically builds and publishes Docker images when code is merged to the main branch.

## Pre-commit Hooks

Pre-commit hooks run automatically before each commit to ensure code quality. They check:

- **Ruff**: Linting and import sorting
- **Black**: Code formatting (as backup check)
- **MyPy**: Type checking
- **Pytest**: Fast unit tests (excludes slow/integration tests)
- **General checks**: Trailing whitespace, YAML/JSON validity, large files, etc.

### Setup

Install pre-commit hooks:

```bash
make install-dev
# or manually:
pre-commit install
```

### Manual Execution

Run pre-commit hooks on all files:

```bash
make pre-commit-run
# or manually:
pre-commit run --all-files
```

### Bypassing Hooks (Not Recommended)

If you need to bypass hooks for a specific commit (e.g., during WIP):

```bash
git commit --no-verify -m "WIP: temporary commit"
```

## CI/CD Pipeline

The CI/CD pipeline is defined in `.github/workflows/ci.yml` and runs on:

- **Push to main/develop**: Runs quality checks and builds/publishes Docker image
- **Pull requests**: Runs quality checks only (no image publishing)

### Pipeline Jobs

#### 1. Quality Checks

Runs on every push and pull request:

- **Ruff linting**: Checks code style and imports
- **Ruff formatting**: Verifies code formatting
- **MyPy type checking**: Validates type annotations
- **Pytest**: Runs test suite with coverage reporting

#### 2. Build and Publish

Runs only on pushes to the `main` branch (after quality checks pass):

- **Docker Buildx**: Builds multi-arch images (amd64, arm64)
- **Image tagging**: Tags with branch name, commit SHA, and `latest`
- **Registry push**: Publishes to GitHub Container Registry (ghcr.io)
- **Layer caching**: Uses GitHub Actions cache for faster builds

### Image Tags

Images are tagged with:

- `latest`: Latest build from main branch
- `main-{sha}`: Specific commit SHA
- `main`: Branch name
- Semantic version tags (if using version tags)

### Registry Configuration

The pipeline uses GitHub Container Registry (ghcr.io) by default. The image name format is:

```
ghcr.io/{username}/{repository}/recipe-ingest:{tag}
```

### Required Secrets

The pipeline uses GitHub's built-in `GITHUB_TOKEN` for registry authentication. No additional secrets are required for GitHub Container Registry.

If using a different registry, configure these secrets in GitHub:

- `DOCKER_REGISTRY_USERNAME`: Registry username
- `DOCKER_REGISTRY_PASSWORD`: Registry password/token
- `DOCKER_REGISTRY_URL`: Registry URL (if not using default)

To set secrets:

1. Go to repository Settings → Secrets and variables → Actions
2. Click "New repository secret"
3. Add each secret with the appropriate value

## Watchtower Integration

Watchtower automatically monitors the container registry for image updates and restarts services when new images are available.

### Configuration

Watchtower is configured in `docker-compose.yml` with:

- **Poll interval**: Checks for updates every 5 minutes (configurable via `WATCHTOWER_POLL_INTERVAL`)
- **Label-based watching**: Only watches containers with `com.centurylinklabs.watchtower.enable=true`
- **Cleanup**: Automatically removes old images after updates
- **Registry authentication**: Supports private registry authentication

### Environment Variables

Set these environment variables in your `.env` file or shell:

```bash
# Docker image to use (defaults to ghcr.io if not set)
DOCKER_IMAGE=ghcr.io/your-username/recipe-pipeline/recipe-ingest:latest

# GitHub username (for default image path)
GITHUB_USERNAME=your-username

# Watchtower configuration
WATCHTOWER_POLL_INTERVAL=300  # seconds (default: 300 = 5 minutes)

# Registry authentication (if using private registry)
DOCKER_REGISTRY_USERNAME=your-username
DOCKER_REGISTRY_PASSWORD=your-token-or-password
DOCKER_CONFIG_PATH=~/.docker  # Path to docker config for auth
```

### Private Registry Authentication

For private registries, you have two options:

#### Option 1: Environment Variables

Set `WATCHTOWER_REPO_USER` and `WATCHTOWER_REPO_PASS` in your environment or `.env` file.

#### Option 2: Docker Config

Create a Docker config file at `~/.docker/config.json`:

```json
{
  "auths": {
    "ghcr.io": {
      "auth": "base64-encoded-username:token"
    }
  }
}
```

Then mount it in docker-compose.yml (already configured).

### GitHub Container Registry Authentication

For GitHub Container Registry, create a Personal Access Token (PAT) with `read:packages` permission:

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate a new token with `read:packages` scope
3. Use it as `DOCKER_REGISTRY_PASSWORD` or in Docker config

### Testing Watchtower

To test Watchtower manually:

```bash
# Check Watchtower logs
docker logs recipe-ingest-watchtower

# Force Watchtower to check for updates immediately
docker exec recipe-ingest-watchtower watchtower --run-once

# Check which containers Watchtower is monitoring
docker exec recipe-ingest-watchtower watchtower --run-once --debug
```

## Local Development vs Production

### Local Development

For local development, you can:

1. **Build locally**: Use `make docker-build` to build from source
2. **Use local image**: Comment out the `image:` line in docker-compose.yml and uncomment `build:`
3. **Skip Watchtower**: Comment out the watchtower service in docker-compose.yml

### Production Deployment

For production:

1. **Use registry image**: Set `DOCKER_IMAGE` environment variable
2. **Enable Watchtower**: Ensure watchtower service is running
3. **Configure authentication**: Set up registry credentials
4. **Monitor logs**: Check Watchtower logs for update notifications

## Workflow

### Typical Development Workflow

1. **Create feature branch**:
   ```bash
   git checkout -b feature/my-feature
   ```

2. **Make changes and commit**:
   ```bash
   git add .
   git commit -m "Add new feature"
   # Pre-commit hooks run automatically
   ```

3. **Push and create PR**:
   ```bash
   git push origin feature/my-feature
   # Create PR on GitHub
   ```

4. **CI runs automatically**:
   - Quality checks run on PR
   - Review and address any failures

5. **Merge to main**:
   - After PR approval, merge to main
   - CI builds and publishes Docker image
   - Watchtower detects update and restarts service

### Manual Image Publishing

To manually trigger a build (if needed):

1. Push a tag:
   ```bash
   git tag v1.0.0
   git push origin v1.0.0
   ```

2. Or push directly to main:
   ```bash
   git push origin main
   ```

## Troubleshooting

### Pre-commit Hooks Not Running

```bash
# Reinstall hooks
make pre-commit-install
# or
pre-commit install
```

### CI Pipeline Failing

1. Check GitHub Actions logs for specific errors
2. Run quality checks locally:
   ```bash
   make qa
   ```
3. Fix issues and push again

### Watchtower Not Updating

1. Check Watchtower logs:
   ```bash
   docker logs recipe-ingest-watchtower
   ```

2. Verify container has the watchtower label:
   ```bash
   docker inspect recipe-ingest-api | grep -A 5 Labels
   ```

3. Check registry authentication:
   ```bash
   docker pull ghcr.io/your-username/recipe-pipeline/recipe-ingest:latest
   ```

4. Verify image exists in registry:
   - Check GitHub Packages page for your repository

### Image Not Found

If you get "image not found" errors:

1. Verify the image was built and pushed (check GitHub Actions logs)
2. Check image name matches your configuration
3. Verify registry authentication
4. Ensure image is not private or you have access

## Best Practices

1. **Always run pre-commit hooks**: Don't bypass unless absolutely necessary
2. **Test locally first**: Run `make qa` before pushing
3. **Small, focused commits**: Easier to review and debug
4. **Meaningful commit messages**: Follow conventional commit format
5. **Monitor CI/CD**: Check pipeline status regularly
6. **Keep dependencies updated**: Regularly update pre-commit hooks and CI actions
7. **Document breaking changes**: Update documentation when making significant changes

## Additional Resources

- [Pre-commit documentation](https://pre-commit.com/)
- [GitHub Actions documentation](https://docs.github.com/en/actions)
- [Watchtower documentation](https://containrrr.dev/watchtower/)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)


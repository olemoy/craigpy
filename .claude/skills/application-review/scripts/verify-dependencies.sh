#!/bin/bash
# verify-dependencies.sh - Factual verification via file existence checks only
# Outputs JSON with verified (not inferred) data
# 
# Minimal approach: Only checks file existence, no package manager commands.
# This avoids complexity with npm/yarn/pnpm/bun/maven/gradle variations.

set -e

REPO_PATH="${1:-.}"
cd "$REPO_PATH"

echo "{"

# 1. Lock file detection
echo '  "lockFiles": {'
LOCK_FILES=()
[ -f "package-lock.json" ] && LOCK_FILES+=("package-lock.json")
[ -f "yarn.lock" ] && LOCK_FILES+=("yarn.lock")
[ -f "pnpm-lock.yaml" ] && LOCK_FILES+=("pnpm-lock.yaml")
[ -f "bun.lockb" ] && LOCK_FILES+=("bun.lockb")
[ -f "Gemfile.lock" ] && LOCK_FILES+=("Gemfile.lock")
[ -f "poetry.lock" ] && LOCK_FILES+=("poetry.lock")
[ -f "Pipfile.lock" ] && LOCK_FILES+=("Pipfile.lock")
[ -f "go.sum" ] && LOCK_FILES+=("go.sum")
[ -f "Cargo.lock" ] && LOCK_FILES+=("Cargo.lock")
[ -f "composer.lock" ] && LOCK_FILES+=("composer.lock")

if [ ${#LOCK_FILES[@]} -eq 0 ]; then
  echo '    "found": false,'
  echo '    "files": []'
else
  echo '    "found": true,'
  printf '    "files": ["%s"' "${LOCK_FILES[0]}"
  for f in "${LOCK_FILES[@]:1}"; do
    printf ', "%s"' "$f"
  done
  echo ']'
fi
echo '  },'

# 2. Package manager detection (by manifest/lock file presence only)
echo '  "packageManager": {'
if [ -f "package.json" ]; then
  if [ -f "yarn.lock" ]; then
    PM="yarn"
  elif [ -f "pnpm-lock.yaml" ]; then
    PM="pnpm"
  elif [ -f "bun.lockb" ]; then
    PM="bun"
  else
    PM="npm"
  fi
  echo "    \"type\": \"$PM\","
  echo '    "manifest": "package.json"'
elif [ -f "pyproject.toml" ]; then
  if [ -f "poetry.lock" ]; then
    echo '    "type": "poetry",'
    echo '    "manifest": "pyproject.toml"'
  elif [ -f "Pipfile.lock" ]; then
    echo '    "type": "pipenv",'
    echo '    "manifest": "Pipfile"'
  else
    echo '    "type": "pip",'
    echo '    "manifest": "pyproject.toml"'
  fi
elif [ -f "requirements.txt" ]; then
  echo '    "type": "pip",'
  echo '    "manifest": "requirements.txt"'
elif [ -f "go.mod" ]; then
  echo '    "type": "go",'
  echo '    "manifest": "go.mod"'
elif [ -f "Cargo.toml" ]; then
  echo '    "type": "cargo",'
  echo '    "manifest": "Cargo.toml"'
elif [ -f "Gemfile" ]; then
  echo '    "type": "bundler",'
  echo '    "manifest": "Gemfile"'
elif [ -f "pom.xml" ]; then
  echo '    "type": "maven",'
  echo '    "manifest": "pom.xml"'
elif [ -f "build.gradle" ] || [ -f "build.gradle.kts" ]; then
  echo '    "type": "gradle",'
  MANIFEST="build.gradle"
  [ -f "build.gradle.kts" ] && MANIFEST="build.gradle.kts"
  echo "    \"manifest\": \"$MANIFEST\""
elif [ -f "composer.json" ]; then
  echo '    "type": "composer",'
  echo '    "manifest": "composer.json"'
else
  echo '    "type": null,'
  echo '    "manifest": null'
fi
echo '  },'

# 3. Security config detection
echo '  "securityConfig": {'
DEPENDABOT="false"
SNYK="false"
RENOVATE="false"
CODEOWNERS="false"
SECURITY_POLICY="false"

[ -f ".github/dependabot.yml" ] || [ -f ".github/dependabot.yaml" ] && DEPENDABOT="true"
[ -f ".snyk" ] && SNYK="true"
[ -f "renovate.json" ] || [ -f ".github/renovate.json" ] && RENOVATE="true"
[ -f "CODEOWNERS" ] || [ -f ".github/CODEOWNERS" ] || [ -f "docs/CODEOWNERS" ] && CODEOWNERS="true"
[ -f "SECURITY.md" ] || [ -f ".github/SECURITY.md" ] && SECURITY_POLICY="true"

echo "    \"dependabot\": $DEPENDABOT,"
echo "    \"snyk\": $SNYK,"
echo "    \"renovate\": $RENOVATE,"
echo "    \"codeowners\": $CODEOWNERS,"
echo "    \"securityPolicy\": $SECURITY_POLICY"
echo '  },'

# 4. CI/CD config detection
echo '  "cicd": {'
GITHUB_ACTIONS="false"
GITLAB_CI="false"
JENKINS="false"
AZURE_PIPELINES="false"
CIRCLECI="false"

[ -d ".github/workflows" ] && [ "$(ls -A .github/workflows 2>/dev/null)" ] && GITHUB_ACTIONS="true"
[ -f ".gitlab-ci.yml" ] && GITLAB_CI="true"
[ -f "Jenkinsfile" ] && JENKINS="true"
[ -f "azure-pipelines.yml" ] && AZURE_PIPELINES="true"
[ -d ".circleci" ] && CIRCLECI="true"

echo "    \"githubActions\": $GITHUB_ACTIONS,"
echo "    \"gitlabCi\": $GITLAB_CI,"
echo "    \"jenkins\": $JENKINS,"
echo "    \"azurePipelines\": $AZURE_PIPELINES,"
echo "    \"circleci\": $CIRCLECI"
echo '  },'

# 5. Container config detection
echo '  "containerization": {'
DOCKERFILE="false"
DOCKER_COMPOSE="false"
KUBERNETES="false"
HELM="false"

[ -f "Dockerfile" ] && DOCKERFILE="true"
[ -f "docker-compose.yml" ] || [ -f "docker-compose.yaml" ] && DOCKER_COMPOSE="true"
[ -d "k8s" ] || [ -d "kubernetes" ] && KUBERNETES="true"
[ -d "helm" ] || [ -d "charts" ] && HELM="true"

echo "    \"dockerfile\": $DOCKERFILE,"
echo "    \"dockerCompose\": $DOCKER_COMPOSE,"
echo "    \"kubernetes\": $KUBERNETES,"
echo "    \"helm\": $HELM"
echo '  },'

# 6. Documentation detection
echo '  "documentation": {'
README="false"
CONTRIBUTING="false"
CHANGELOG="false"
ADR="false"

[ -f "README.md" ] || [ -f "readme.md" ] && README="true"
[ -f "CONTRIBUTING.md" ] && CONTRIBUTING="true"
[ -f "CHANGELOG.md" ] || [ -f "HISTORY.md" ] && CHANGELOG="true"
[ -d "docs/adr" ] || [ -d "doc/adr" ] || [ -d ".adr" ] || [ -d "architecture/decisions" ] && ADR="true"

echo "    \"readme\": $README,"
echo "    \"contributing\": $CONTRIBUTING,"
echo "    \"changelog\": $CHANGELOG,"
echo "    \"adr\": $ADR"
echo '  }'

echo "}"

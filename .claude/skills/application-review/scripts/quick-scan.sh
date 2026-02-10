#!/bin/bash
# quick-scan.sh - Fast directory scan to inventory repositories
# Usage: quick-scan.sh [base-path]
# Output: JSON with repository inventory for agent to present to user
#
# Example:
#   bash scripts/quick-scan.sh /path/to/repos
#   bash scripts/quick-scan.sh .

set -e

BASE="${1:-.}"

# Resolve to absolute path
BASE=$(cd "$BASE" && pwd)

echo "{"
echo "  \"basePath\": \"$BASE\","
echo "  \"scannedAt\": \"$(date -u +"%Y-%m-%dT%H:%M:%SZ")\","
echo "  \"repositories\": ["

first=true
for dir in "$BASE"/*/; do
  [ -d "$dir" ] || continue
  
  # Detect if it's a code repository (has common indicators)
  IS_REPO=false
  [ -d "$dir/.git" ] && IS_REPO=true
  [ -f "$dir/package.json" ] && IS_REPO=true
  [ -f "$dir/pom.xml" ] && IS_REPO=true
  [ -f "$dir/build.gradle" ] || [ -f "$dir/build.gradle.kts" ] && IS_REPO=true
  [ -f "$dir/go.mod" ] && IS_REPO=true
  [ -f "$dir/Cargo.toml" ] && IS_REPO=true
  [ -f "$dir/requirements.txt" ] || [ -f "$dir/pyproject.toml" ] && IS_REPO=true
  [ -f "$dir/Gemfile" ] && IS_REPO=true
  [ -f "$dir/composer.json" ] && IS_REPO=true
  
  $IS_REPO || continue
  
  $first || echo ","
  first=false
  
  NAME=$(basename "$dir")
  
  # Detect primary language/type
  TYPE="unknown"
  LANG="unknown"
  FRAMEWORK=""
  
  if [ -f "$dir/package.json" ]; then
    TYPE="node"
    LANG="TypeScript/JavaScript"
    # Check for framework indicators
    if grep -q '"next"' "$dir/package.json" 2>/dev/null; then
      FRAMEWORK="Next.js"
    elif grep -q '"react"' "$dir/package.json" 2>/dev/null; then
      FRAMEWORK="React"
    elif grep -q '"vue"' "$dir/package.json" 2>/dev/null; then
      FRAMEWORK="Vue"
    elif grep -q '"express"' "$dir/package.json" 2>/dev/null; then
      FRAMEWORK="Express"
    fi
  elif [ -f "$dir/build.gradle.kts" ]; then
    TYPE="gradle"
    LANG="Kotlin"
    if grep -q "spring" "$dir/build.gradle.kts" 2>/dev/null; then
      FRAMEWORK="Spring Boot"
    fi
  elif [ -f "$dir/build.gradle" ]; then
    TYPE="gradle"
    LANG="Java/Kotlin"
    if grep -q "spring" "$dir/build.gradle" 2>/dev/null; then
      FRAMEWORK="Spring Boot"
    fi
  elif [ -f "$dir/pom.xml" ]; then
    TYPE="maven"
    LANG="Java"
    if grep -q "spring-boot" "$dir/pom.xml" 2>/dev/null; then
      FRAMEWORK="Spring Boot"
    fi
  elif [ -f "$dir/go.mod" ]; then
    TYPE="go"
    LANG="Go"
  elif [ -f "$dir/Cargo.toml" ]; then
    TYPE="cargo"
    LANG="Rust"
  elif [ -f "$dir/pyproject.toml" ] || [ -f "$dir/requirements.txt" ]; then
    TYPE="python"
    LANG="Python"
    if [ -f "$dir/pyproject.toml" ] && grep -q "django" "$dir/pyproject.toml" 2>/dev/null; then
      FRAMEWORK="Django"
    elif [ -f "$dir/pyproject.toml" ] && grep -q "fastapi" "$dir/pyproject.toml" 2>/dev/null; then
      FRAMEWORK="FastAPI"
    fi
  elif [ -f "$dir/Gemfile" ]; then
    TYPE="ruby"
    LANG="Ruby"
    if grep -q "rails" "$dir/Gemfile" 2>/dev/null; then
      FRAMEWORK="Rails"
    fi
  elif [ -f "$dir/composer.json" ]; then
    TYPE="php"
    LANG="PHP"
  fi
  
  # Check for key files
  HAS_README="false"
  HAS_DOCKERFILE="false"
  HAS_CI="false"
  
  [ -f "$dir/README.md" ] || [ -f "$dir/readme.md" ] && HAS_README="true"
  [ -f "$dir/Dockerfile" ] && HAS_DOCKERFILE="true"
  [ -d "$dir/.github/workflows" ] || [ -f "$dir/.gitlab-ci.yml" ] || [ -f "$dir/Jenkinsfile" ] && HAS_CI="true"
  
  # Count source files (approximate)
  FILE_COUNT=$(find "$dir" -type f \( -name "*.ts" -o -name "*.tsx" -o -name "*.js" -o -name "*.jsx" -o -name "*.kt" -o -name "*.java" -o -name "*.py" -o -name "*.go" -o -name "*.rs" -o -name "*.rb" -o -name "*.php" \) 2>/dev/null | wc -l | tr -d ' ')
  
  echo -n "    {"
  echo -n "\"name\": \"$NAME\", "
  echo -n "\"type\": \"$TYPE\", "
  echo -n "\"language\": \"$LANG\""
  [ -n "$FRAMEWORK" ] && echo -n ", \"framework\": \"$FRAMEWORK\""
  echo -n ", \"hasReadme\": $HAS_README"
  echo -n ", \"hasDockerfile\": $HAS_DOCKERFILE"
  echo -n ", \"hasCI\": $HAS_CI"
  echo -n ", \"sourceFileCount\": $FILE_COUNT"
  echo -n "}"
done

echo ""
echo "  ]"
echo "}"

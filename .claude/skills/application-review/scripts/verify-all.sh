#!/bin/bash
# verify-all.sh - Run verification on one or more repositories
# Usage: verify-all.sh repo1 [repo2] [repo3] ...
# Output: Combined JSON object with results per repository
#
# Example:
#   bash scripts/verify-all.sh ./app1 ./app2 ./app3
#   bash scripts/verify-all.sh /path/to/repos/*

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ $# -eq 0 ]; then
  echo "Usage: verify-all.sh repo1 [repo2] [repo3] ..." >&2
  echo "Example: verify-all.sh ./my-app ../other-app" >&2
  exit 1
fi

echo "{"
echo '  "generatedAt": "'$(date -u +"%Y-%m-%dT%H:%M:%SZ")'",'
echo '  "repositoryCount": '$#','
echo '  "repositories": {'

first=true
for repo in "$@"; do
  # Skip if not a directory
  if [ ! -d "$repo" ]; then
    echo "Warning: $repo is not a directory, skipping" >&2
    continue
  fi
  
  $first || echo "    ,"
  first=false
  
  REPO_NAME=$(basename "$repo")
  REPO_PATH=$(cd "$repo" && pwd)
  
  echo "    \"$REPO_NAME\": {"
  echo "      \"path\": \"$REPO_PATH\","
  echo "      \"verification\": {"
  
  # Run verify-dependencies.sh and indent its output
  "$SCRIPT_DIR/verify-dependencies.sh" "$repo" 2>/dev/null | \
    grep -v '^{$' | grep -v '^}$' | \
    sed 's/^  /        /'
  
  echo "      }"
  echo "    }"
done

echo "  }"
echo "}"

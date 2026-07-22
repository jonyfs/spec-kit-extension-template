#!/usr/bin/env bash
# Principle III: template placeholders must be obvious, and must never survive
# into something a user would publish.
#
# The template's OWN files are supposed to contain CUSTOMIZE markers — that is
# the entire point of a template. What must never happen is a *generated* or
# *vendored* extension package still carrying them. This script draws that line.

set -euo pipefail

# Paths that are allowed to contain placeholder markers, because they ARE the
# template surface authors copy from.
ALLOWED_PREFIXES=(
  "./template/"
  "./docs/"
  "./scripts/check-placeholders.sh"
  "./scripts/validate-extension.py"
  "./.specify/memory/constitution.md"
)

MARKERS='CUSTOMIZE:|REPLACE THIS|my-extension|your-org|spec-kit-my-ext'

is_allowed() {
  local path="$1" prefix
  for prefix in "${ALLOWED_PREFIXES[@]}"; do
    [[ "$path" == "$prefix"* ]] && return 0
  done
  return 1
}

violations=0

# Only consider extension packages — a directory containing an extension.yml.
while IFS= read -r manifest; do
  package_dir="$(dirname "$manifest")"

  # Vendored third-party extensions are governed by their own authors.
  if [[ "$package_dir" == ./.specify/extensions/* ]]; then
    continue
  fi

  while IFS= read -r hit; do
    file="${hit%%:*}"
    is_allowed "$file" && continue
    echo "ERROR: $hit"
    violations=$((violations + 1))
  done < <(grep -rInE "$MARKERS" "$package_dir" 2>/dev/null || true)
done < <(find . -name extension.yml -not -path './.git/*')

if [ "$violations" -gt 0 ]; then
  echo
  echo "Found $violations placeholder marker(s) in extension packages."
  echo "Resolve every CUSTOMIZE marker before releasing (constitution Principle III)."
  exit 1
fi

echo "No unresolved template placeholders in any extension package."

#!/usr/bin/env bash
# Concatenate the public text files of survey-skill into one .txt file, for
# AI web services that accept only a single uploaded file. Each entry is a
# "FILE: path" header followed by the verbatim content.
#
# Usage: scripts/make_bundle.sh [output.txt]
#        (default: dist/survey-skill-bundle.txt, git-ignored)
set -euo pipefail
cd "$(dirname "$0")/.."

# The manifest: every public file worth feeding to an AI, in reading order.
# Docs first, then the validator, then the sample surveys.
FILES=(
  README.md
  instructions/guide.md
  instructions/FAQ.md
  skills/survey-qsf/SKILL.md
  skills/survey-qsf/references/sso.md
  skills/survey-qsf/references/feature-shapes.md
  skills/survey-qsf/scripts/validate_qsf.py
  skills/survey-qsf/samples/session-availability-sso.qsf
  skills/survey-qsf/samples/ranked-preferences-sso.qsf
  skills/survey-qsf/samples/event-attendance-sso.qsf
)

OUT="${1:-dist/survey-skill-bundle.txt}"

missing=0
for f in "${FILES[@]}"; do
  [ -f "$f" ] || { echo "make_bundle: missing file: $f" >&2; missing=1; }
done
[ "$missing" -eq 0 ] || exit 1

mkdir -p "$(dirname "$OUT")"
TMP="$(mktemp "${OUT}.XXXXXX")"
trap 'rm -f "$TMP"' EXIT

SEP="$(printf '=%.0s' {1..79})"
{
  echo "$SEP"
  echo "# survey-skill single-file bundle"
  commit="$(git rev-parse --short HEAD 2>/dev/null || true)"
  echo "# generated $(date -u +%Y-%m-%dT%H:%M:%SZ)${commit:+ from commit $commit}"
  echo "# ${#FILES[@]} files. Sections start with: FILE: <path>"
  for f in "${FILES[@]}"; do
    echo "$SEP"
    echo "FILE: $f"
    echo "$SEP"
    cat "$f"
    echo
  done
} > "$TMP"
mv "$TMP" "$OUT"

echo "wrote $OUT ($(wc -c < "$OUT") bytes, ${#FILES[@]} files)"

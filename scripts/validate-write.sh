#!/usr/bin/env bash
#
# validate-write.sh — Validate .md files in ~/second-brain/
#
# Usage: validate-write.sh <file-path>
#
# Checks:
#   1. File has YAML frontmatter (--- block)
#   2. Frontmatter has 'tags:' and 'date:' fields
#   3. Files >300 chars have at least one [[wikilink]]
#
# Skips: templates/, .obsidian/, scripts/ directories
#
# Exit: 0 on PASS, 1 on FAIL

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: validate-write.sh <file-path>" >&2
    exit 1
fi

FILE="$1"

# Check file exists
if [[ ! -f "$FILE" ]]; then
    echo "FAIL: file does not exist: $FILE"
    exit 1
fi

# Skip directories that don't need validation
case "$FILE" in
    */templates/*|*/.obsidian/*|*/scripts/*)
        echo "PASS: skipped (excluded directory)"
        exit 0
        ;;
esac

# Only validate .md files
if [[ "$FILE" != *.md ]]; then
    echo "PASS: skipped (not a .md file)"
    exit 0
fi

CONTENT=$(cat "$FILE")

# Check 1: Has frontmatter block (starts with --- and has closing ---)
FIRST_LINE=$(head -n 1 "$FILE")
if [[ "$FIRST_LINE" != "---" ]]; then
    echo "FAIL: missing YAML frontmatter (file must start with ---)"
    exit 1
fi

# Find closing --- (line 2+)
CLOSING_LINE=$(tail -n +2 "$FILE" | grep -n "^---$" | head -1 | cut -d: -f1)
if [[ -z "$CLOSING_LINE" ]]; then
    echo "FAIL: frontmatter block not closed (missing closing ---)"
    exit 1
fi

# Extract frontmatter (between the two --- lines)
FRONTMATTER=$(head -n $((CLOSING_LINE + 1)) "$FILE" | tail -n +2 | head -n $((CLOSING_LINE - 1)))

# Check 2: Frontmatter has 'tags:' field
if ! echo "$FRONTMATTER" | grep -q "^tags:"; then
    echo "FAIL: frontmatter missing 'tags:' field"
    exit 1
fi

# Check 3: Frontmatter has 'date:' field
if ! echo "$FRONTMATTER" | grep -q "^date:"; then
    echo "FAIL: frontmatter missing 'date:' field"
    exit 1
fi

# Check 4: Files >300 chars must have at least one [[wikilink]]
CHAR_COUNT=${#CONTENT}
if [[ $CHAR_COUNT -gt 300 ]]; then
    if ! grep -q '\[\[.*\]\]' "$FILE"; then
        echo "FAIL: file has ${CHAR_COUNT} chars but no [[wikilink]] found (required for notes >300 chars)"
        exit 1
    fi
fi

# Check 5: Title-as-proposition for notes in A.DIVA/wiki/ (excluding MOCs)
case "$FILE" in
    */A.DIVA/wiki/*)
        # Skip MOC files — they are indexes, not claims
        case "$FILE" in
            */MOCs/*) ;;
            *)
                # Extract title from first # heading
                TITLE=$(grep -m1 "^# " "$FILE" | sed 's/^# //')
                if [[ -n "$TITLE" ]]; then
                    # Count words
                    WORD_COUNT=$(echo "$TITLE" | wc -w | tr -d ' ')
                    if [[ $WORD_COUNT -lt 3 ]]; then
                        echo "WARN: title '$TITLE' has only $WORD_COUNT words — may be a topic label, not a proposition"
                        # WARN, not FAIL — allows override
                    fi
                    # Check for Title Case (all words capitalized = likely a topic label)
                    TITLE_CASE=$(echo "$TITLE" | awk '{for(i=1;i<=NF;i++) if($i ~ /^[A-ZÀ-Ú]/) c++; print c+0"/"NF}')
                    TC_NUM=$(echo "$TITLE_CASE" | cut -d/ -f1)
                    TC_DEN=$(echo "$TITLE_CASE" | cut -d/ -f2)
                    if [[ $TC_DEN -gt 2 && $TC_NUM -eq $TC_DEN ]]; then
                        echo "WARN: title '$TITLE' appears to be Title Case — prefer lowercase prose-as-proposition"
                    fi
                fi
                ;;
        esac
        ;;
esac

echo "PASS"
exit 0

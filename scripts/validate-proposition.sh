#!/usr/bin/env bash
# validate-proposition.sh — Check if a note title reads as a proposition
# Usage: validate-proposition.sh <filepath>
#
# A good evergreen note title can be prefixed with "This note argues that..."
# and still read as a complete sentence. Topic labels like "Carbon Markets"
# or "Docker Setup" are NOT propositions.
#
# Exit codes:
#   0 = title is a proposition (or close enough)
#   1 = title looks like a topic label (needs rewriting)
#   2 = error (file not found, no heading found)

set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: validate-proposition.sh <filepath>"
    exit 2
fi

filepath="${1/#\~/$HOME}"

if [[ ! -f "$filepath" ]]; then
    echo "ERROR: File not found: $filepath"
    exit 2
fi

# Extract title from first # heading (level 1 or 2)
title=$(grep -m1 '^#\{1,2\} ' "$filepath" | sed 's/^#\{1,2\} //' | sed 's/^[[:space:]]*//' | sed 's/[[:space:]]*$//')

if [[ -z "$title" ]]; then
    echo "ERROR: No heading found in $filepath"
    exit 2
fi

# Remove emoji prefixes (common in Obsidian)
clean_title=$(echo "$title" | sed 's/^[^[:alnum:]]*//;s/[[:space:]]*$//')

if [[ -z "$clean_title" ]]; then
    echo "ERROR: Title is empty after cleanup"
    exit 2
fi

# Count words
word_count=$(echo "$clean_title" | wc -w | tr -d ' ')

# --- Heuristic checks ---

is_proposition=true
reasons=()

# 1. Too short (1-2 words) — likely a topic label
if [[ "$word_count" -le 2 ]]; then
    is_proposition=false
    reasons+=("Too short ($word_count words) — likely a topic label")
fi

# 2. Starts with a capital noun pattern without a verb (title case, all words capitalized)
# Count capitalized words (excluding first word, articles, prepositions)
if [[ "$word_count" -ge 3 ]]; then
    cap_count=0
    total=0
    for word in $clean_title; do
        total=$((total + 1))
        if [[ "$total" -eq 1 ]]; then continue; fi
        # Skip common lowercase words
        case "$word" in
            a|an|the|of|in|on|at|to|for|and|or|but|is|are|was|were|de|do|da|dos|das|e|o|um|uma|no|na|nos|nas|com|por|para|em|que) continue ;;
        esac
        if [[ "$word" =~ ^[A-Z] ]]; then
            cap_count=$((cap_count + 1))
        fi
    done
    # If most content words are capitalized, it's likely Title Case (a label)
    content_words=$((total - 1))
    if [[ "$content_words" -gt 0 && "$cap_count" -gt 0 ]]; then
        ratio=$((cap_count * 100 / content_words))
        if [[ "$ratio" -ge 80 ]]; then
            is_proposition=false
            reasons+=("Title Case detected — looks like a topic heading, not a claim")
        fi
    fi
fi

# 3. Contains a verb indicator (good sign for propositions)
# Look for common verb patterns in English and Portuguese
has_verb=false
lower_title=$(echo "$clean_title" | tr '[:upper:]' '[:lower:]')
# English verb indicators
if echo "$lower_title" | grep -qiE '\b(is|are|was|were|has|have|had|does|do|did|can|could|should|would|will|shall|must|may|might|need|needs|make|makes|enable|enables|create|creates|cause|causes|lead|leads|require|requires|prevent|prevents|allow|allows|suggest|suggests|imply|implies|mean|means|prove|proves|show|shows|demonstrate|demonstrates|reduce|reduces|increase|increases|improve|improves|drive|drives|determine|determines|influence|influences|affect|affects|produce|produces|generate|generates|transform|transforms|emerge|emerges|become|becomes|depend|depends|connect|connects|extend|extends|contradict|contradicts|support|supports|challenge|challenges|explain|explains|predict|predicts|result|results)\b'; then
    has_verb=true
fi
# Portuguese verb indicators
if echo "$lower_title" | grep -qiE '\b(é|são|foi|foram|eram|está|estão|tem|têm|tinha|faz|fazem|pode|podem|deve|devem|precisa|precisam|permite|permitem|causa|causam|leva|levam|requer|requerem|previne|previnem|sugere|sugerem|implica|implicam|significa|significam|prova|provam|mostra|mostram|demonstra|demonstram|reduz|reduzem|aumenta|aumentam|melhora|melhoram|determina|determinam|influencia|influenciam|afeta|afetam|produz|produzem|gera|geram|transforma|transformam|emerge|emergem|depende|dependem|conecta|conectam|estende|estendem|contradiz|contradizem|apoia|apoiam|desafia|desafiam|explica|explicam|prediz|predizem|resulta|resultam|cria|criam|torna|tornam|exige|exigem)\b'; then
    has_verb=true
fi

if [[ "$has_verb" == false && "$word_count" -ge 3 ]]; then
    is_proposition=false
    reasons+=("No verb detected — propositions typically contain a verb")
fi

# 4. Ends with a noun-heavy pattern (e.g., "Machine Learning Infrastructure")
# This is hard to detect perfectly, so we just flag very short verbless titles
if [[ "$word_count" -le 4 && "$has_verb" == false ]]; then
    is_proposition=false
    reasons+=("Short and verbless — reads as a category, not an argument")
fi

# --- Output ---

echo "Title: \"$clean_title\""
echo "Words: $word_count"
echo ""

if [[ "$is_proposition" == true ]]; then
    echo "PASS — Title reads as a proposition."
    echo "Test: \"This note argues that $clean_title\" ✓"
    exit 0
else
    echo "FAIL — Title looks like a topic label, not a proposition."
    for reason in "${reasons[@]}"; do
        echo "  - $reason"
    done
    echo ""
    echo "Test: \"This note argues that $clean_title\" ← does this read as a sentence?"
    echo ""
    echo "Consider rewriting as a claim. Examples:"
    echo "  BAD:  'Carbon Markets'"
    echo "  GOOD: 'Carbon markets need transparent verification to scale'"
    echo "  BAD:  'Docker Setup'"
    echo "  GOOD: 'Container orchestration reduces deployment complexity'"
    exit 1
fi

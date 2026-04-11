# Knowledge Engine — User Guide

## Quick Reference

| I want to... | Type this | How long it takes |
|---|---|---|
| Save a document to my library | `/reduce` | 2-5 minutes |
| Search my knowledge | `/knowledge-search` | A few seconds |
| Quick-capture a thought | `/dump` | Under a minute |
| Start my day with a briefing | `/standup` | A few seconds |
| Save a good answer as a note | `/file-note` | Under a minute |
| Find connections between notes | `/reflect` | 1-2 minutes |
| Check my notes' quality | `/verify` | 1-2 minutes |
| Check my vault's health | `/lint` | 2-3 minutes |
| End my session cleanly | `/wrap-up` | Under a minute |

Just type the command in the Claude Code chat. Claude will guide you through the rest.

---

## 1. Save a Document (`/reduce`)

**When to use it:** You have a PDF, article, or notes you want to add to your knowledge library.

**What to do:**
1. Upload the file to Claude (drag and drop, or use the attachment button)
2. Type `/reduce`
3. Claude will show you the file and ask you to confirm

**What happens behind the scenes:**
- Claude sends the file to the knowledge archive on the Mac Mini
- It reads the document and extracts the key ideas
- Each idea becomes a separate note in your wiki
- It checks for duplicates — if you already have a similar note, it merges instead of creating a new one
- It creates links to related notes that already exist in your vault

**What you'll see:**
Claude will present a list of the ideas it found and ask for your approval before creating the notes. You can say "yes" to create all of them, or ask Claude to skip or modify specific ones.

**Example:**
```
You: [upload climate-report.pdf]
You: /reduce

Claude: I found the file climate-report.pdf in your inbox. Shall I process it?

You: yes

Claude: I've read the document and extracted 5 claims:
1. "Direct air capture costs are declining faster than projected"
2. "Carbon credit markets lack standardized verification"
...
Shall I create these as wiki notes?

You: yes

Claude: Done! Created 5 notes in A.DIVA/wiki/. Source archived in B.TEJO/knowledge/.
```

---

## 2. Search My Knowledge (`/knowledge-search`)

**When to use it:** You want to find something you've saved before, or ask a question that your library might answer.

**What to do:**
1. Type `/knowledge-search`
2. Ask your question naturally — in English or Portuguese

**What happens:**
- Claude first searches your Obsidian vault (the wiki notes you've built up)
- If it finds a good answer there, it uses it — this is fast and draws on your curated knowledge
- If the vault doesn't have enough, Claude searches the full document archive on the Mac Mini
- If the answer combines multiple sources into something new, Claude may suggest saving it as a permanent note

**Example:**
```
You: /knowledge-search
You: What do I know about carbon credit verification?

Claude: Found 3 relevant notes in your wiki:
- [[carbon-credit-markets-lack-standardized-verification]]
- [[blockchain-could-improve-carbon-credit-transparency]]
- [[ieta-report-key-findings]]

Based on your notes: Carbon credit markets currently lack standardized
verification, which limits their scalability. The IETA report suggests...

This combines insights from 2+ sources. Want me to save this synthesis
as a permanent note? (/file-note)
```

---

## 3. Quick-Capture a Thought (`/dump`)

**When to use it:** You have a thought, decision, idea, or observation and want to save it in the right place without thinking about where it goes.

**What to do:**
1. Type `/dump`
2. Write or paste your thought

**What happens:**
Claude reads your message and figures out what kind of thing it is:
- A **decision** you made? Goes to your Key Decisions log
- A **win** or achievement? Goes to today's daily note
- Something about a **person**? Goes to their profile in C.CRM
- A **project update**? Goes to the project file
- An **idea** or something to research later? Goes to your inbox

**Example:**
```
You: /dump
You: Decided to focus Carbon13 pitch on DAC+ocean alkalinity combo
     instead of pure DAC. The cost curve projections are more favorable.

Claude: Classified as DECISION.
Appended to A.DIVA/brain/Key Decisions.md with today's date.
Committed to vault.
```

---

## 4. Start My Day (`/standup`)

**When to use it:** Beginning of your work session. Gives you a quick overview of where things stand.

**What to do:**
1. Type `/standup`

**What you'll see:**
- Your North Star goals (what you're focused on right now)
- Items in your inbox waiting to be processed
- Your current focus area
- Your last few daily notes
- How many notes are in your wiki
- Whether the knowledge archive is online

**Example:**
```
You: /standup

Claude:
=== Good morning ===

North Star:
- Carbon13 (10th Cohort, Cambridge) — departing late April 2026
- Climate tech venture building

Inbox: 3 items waiting
- climate-report-march.pdf
- meeting-notes-investor-call.md
- interesting-article-DAC.md

Recent days: Apr 10 (6 notes), Apr 9 (3 notes), Apr 8 (2 notes)
Wiki: 150 notes across 5 domains
Knowledge API: online (600 documents in archive)
```

---

## 5. Save a Good Answer (`/file-note`)

**When to use it:** Claude just gave you a really good answer that combined multiple sources — and you want to keep it permanently in your wiki.

**What to do:**
1. After receiving a synthesis or insight from Claude that you want to keep
2. Type `/file-note`

**What happens:**
- Claude looks at its last answer
- It checks if it qualifies as a synthesis (combined 2+ sources, produced something new)
- It checks for duplicates in your existing wiki
- It creates a permanent note with proper links and metadata

**Example:**
```
You: /file-note

Claude: Filing the synthesis about carbon capture cost curves.
Title: "DAC and ocean alkalinity cost curves are converging toward $200/ton by 2030"
Sources: [[ieta-report-key-findings]], [[dac-costs-declining-faster-than-projected]]
Confidence: medium

Created: A.DIVA/wiki/2026-04-11-dac-ocean-alkalinity-cost-convergence.md
Updated: MOC-Climate.md
```

---

## 6. Find Connections (`/reflect`)

**When to use it:** After adding a batch of new notes (via `/reduce`), or when you want Claude to find links between your existing knowledge.

**What to do:**
1. Type `/reflect`
2. Optionally, name a specific note: `/reflect` and then mention the note

**What happens:**
- Claude reads your recent notes
- It searches the vault for related ideas
- For each connection it finds, it explains *why* they're connected (not just "these seem related")
- It adds links in both directions — if note A links to note B, note B also links back to A
- It updates the Maps of Content (the domain indexes)

**Example:**
```
You: /reflect

Claude: Reflecting on 3 recently added notes...

Connections found:
1. [[dac-costs-declining]] extends [[carbon-capture-overview]]
   Because: the new cost data adds concrete evidence to the general overview

2. [[ocean-alkalinity-shows-promise]] contradicts [[dac-is-the-only-scalable-approach]]
   Because: ocean alkalinity offers a competing pathway at potentially lower cost

MOC updates:
- Added 2 entries to MOC-Climate

Notes touched: 4 files updated with new wikilinks.
```

---

## 7. Check My Notes' Quality (`/verify`)

**When to use it:** After creating new notes (via `/reduce` or `/file-note`), to make sure they meet quality standards.

**What to do:**
1. Type `/verify`

**What it checks (6 things):**
1. **Title quality** — Does the title state a clear idea? ("Carbon markets need verification" is good; "Carbon Markets" is too vague)
2. **Duplicates** — Is this note too similar to one that already exists?
3. **Source cited** — Does the note say where the information came from?
4. **Correct type** — Is the note labeled as the right type (claim, concept, etc.)?
5. **Links present** — Does the note link to at least 2 other notes?
6. **Reasonable length** — Is the note too long? (Each note should be focused on one idea)

**What you'll see:**
A table showing pass/fail for each check, with suggestions for fixing any issues. Claude will ask if you want it to fix the problems automatically.

---

## 8. Check My Vault's Health (`/lint`)

**When to use it:** Once a week, or whenever you want a big-picture view of your vault's state. Like a health checkup for your knowledge library.

**What to do:**
1. Type `/lint`

**What it checks:**
- **Broken links** — Notes that link to other notes that don't exist
- **Orphan notes** — Notes that nothing else links to (isolated knowledge)
- **Stale claims** — Notes older than 18 months that haven't been reviewed
- **Missing counterpoints** — For your strongest claims, are there opposing views documented?

**What you'll see:**
A health report saved to your vault, plus a summary in the chat. Any issues that need your attention will be clearly listed.

---

## 9. End My Session (`/wrap-up`)

**When to use it:** When you're done working and want to save everything cleanly.

**What to do:**
1. Type `/wrap-up`

**What happens:**
- Updates the search index so new notes are findable
- Commits all vault changes to git (your backup)
- Logs what happened during this session
- Optionally runs a quick quality check on notes you created today

---

## Troubleshooting

### "Claude says the Knowledge API is down"

The document archive runs on the Mac Mini. If it's down:
- Your vault still works (searching notes, creating notes, etc.)
- Only saving new documents (`/reduce`) and searching the archive won't work
- Ask Matheus to check the Mac Mini

### "Claude says qmd is not installed"

qmd is the local search tool. Ask Matheus to run `/setup` on your computer.

### "I made a mistake in my vault"

Don't worry. Everything is tracked in git. Matheus can undo any change. Just tell him what happened.

### "I don't know which command to use"

You don't have to memorize the commands. Just describe what you want in plain language:

- "I want to save this PDF" — Claude will suggest `/reduce`
- "What do I know about X?" — Claude will search your vault
- "I had a thought about..." — Claude will suggest `/dump`

Claude understands your intent and will guide you to the right command.

### "Claude keeps asking about frontmatter"

When you create markdown files in your vault, Claude checks that they have the right metadata (tags, date). This is automatic — just follow Claude's suggestions if it flags something.

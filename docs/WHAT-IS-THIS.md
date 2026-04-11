# Your Personal Knowledge Library

## The Problem

We read articles, save PDFs, bookmark web pages, take notes during meetings, have deep conversations about topics we care about... and forget most of it. Three months later, when we need that specific insight about carbon markets or that framework someone mentioned in a talk, we can't find it. Our knowledge is scattered across apps, folders, browser tabs, and our memory.

## The Solution

This plugin turns Claude into your personal librarian. When you give it a document — a PDF, an article, a set of notes — it reads it, pulls out the important ideas, and files them in your Obsidian vault. Each idea becomes its own note, connected to related ideas you've already saved.

When you ask a question later, Claude checks your vault first. If the answer is already there — in notes you've built up over weeks and months — it uses that. If not, it digs into the full document archive to find what you need, and saves the answer for next time.

Over time, your vault stops being a folder of files and becomes a web of connected knowledge — a personal encyclopedia that grows smarter with every document you add.

## How It Thinks About Your Knowledge

Think of it like a physical library with three parts:

### The Archive (the back room)

Your original documents live here — the actual PDFs, articles, and web clips you've collected. They're stored on the Mac Mini and are searchable, but they're raw material. You don't browse the archive directly; the librarian does that for you.

### The Wiki (the shelves)

This is where the real value lives. When Claude reads a document from the archive, it doesn't just store it — it creates short, focused notes in your Obsidian vault. Each note captures one idea, one claim, one concept. These notes have clear titles that tell you what they argue (not vague labels like "Carbon Markets" but specific claims like "Carbon markets need transparent verification to scale").

Your wiki lives in your vault under `A.DIVA/wiki/`. You can open any note in Obsidian and read it — they're just markdown files.

### The Connections (the librarian's knowledge)

The most valuable part is what happens between the notes. Claude actively finds and creates links: this climate paper relates to that business case, this person's research supports that technical claim, this new finding contradicts something you saved last month.

These connections are visible as `[[wikilinks]]` in your notes — click one in Obsidian and you jump to the related note. Maps of Content (MOCs) organize notes by domain: Technology, Climate, Business, People, Methodology.

## What "Compounding Knowledge" Means

Unlike a regular conversation with an AI — where each chat starts from scratch — this system remembers and builds on itself. When you add your 50th document about climate technology, Claude doesn't process it in isolation. It connects it to the 49 documents you've already added: "This new paper supports the claim from document #12, contradicts a finding from document #31, and introduces a concept that extends what we learned in document #45."

This is the compounding effect. Early documents create the foundation. Later documents land in a rich context, making each new addition more valuable than the last. After a few months, your vault becomes genuinely useful — a knowledge base that reflects your specific interests, reading history, and intellectual journey.

## Your Vault, Your Knowledge

Everything lives in your Obsidian vault — a folder of plain text files on your computer, synced through git. You own every file. You can read them, edit them, reorganize them, or export them. Nothing is locked in a proprietary format or hidden behind an API.

The vault is organized into zones:

| Zone | What's there | Who writes |
|------|-------------|------------|
| **00-inbox** | New stuff waiting to be processed | You drop things here |
| **01-projects** | Your active projects | You (Claude only reads) |
| **02-areas** | Your areas of responsibility | You (Claude only reads) |
| **03-resources** | Reference material | You (Claude only reads) |
| **A.DIVA/wiki** | The knowledge wiki | Claude maintains this |
| **A.DIVA/brain** | Goals, key decisions, patterns | Claude maintains this |
| **B.TEJO** | Document records from the archive | Automatic (don't edit) |
| **C.CRM** | People and relationships | Both (you and Claude) |
| **D.DAILY** | Daily journal | Both (Claude prepares, you write) |

The important thing: zones 01 through 03 are yours. Claude reads them to understand context, but never writes there unless you specifically ask. The wiki, brain, and daily zones are shared spaces where Claude actively helps.

## The Eight Types of Notes

Every note in the wiki has a type, so you always know what kind of knowledge you're looking at:

| Type | What it is | Example |
|------|-----------|---------|
| **Claim** | A specific argument or insight | "Container orchestration reduces deployment complexity" |
| **Concept** | A definition or explanation | "What is Direct Air Capture" |
| **Person** | A profile of someone relevant | "Andrej Karpathy — AI researcher, LLM wiki inventor" |
| **Project** | A project you're tracking | "Carbon13 Cohort 10" |
| **Event** | Something that happened | "IETA Conference 2026" |
| **Decision** | A choice you made and why | "Chose Qdrant over Pinecone for vector search" |
| **Document** | A summary of something you read | "Summary of IETA Brazil Carbon Market Report" |
| **Synthesis** | A new insight combining multiple sources | "Carbon capture and credit markets are converging" |

Syntheses are the most valuable type — they represent genuinely new understanding that didn't exist in any single document. The system creates these when it notices that combining ideas from different sources produces something new.

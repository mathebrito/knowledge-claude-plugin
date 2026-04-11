# Obsidian Setup — Required Configuration

Complete configuration for the Obsidian vault that powers the Knowledge Engine.
Everything here is required for the system to work end-to-end: git sync,
daily notes, templates, and community plugins.

---

## Git Repository

The vault must be a git repo with an SSH remote:

```
~/second-brain/.git        # local repo
origin → git@github.com:mathebrito/second-brain.git
```

Branch: `main` (single-branch workflow — no feature branches for vault content).

---

## Community Plugins (Required)

Enable in: `Settings → Community Plugins → Turn on community plugins`

| Plugin | Purpose | Required? |
|--------|---------|-----------|
| **obsidian-git** | Auto-commit, auto-push, auto-pull — keeps vault synced across machines | Yes |
| **dataview** | Query engine for frontmatter — powers dynamic indexes and MOC views | Yes |
| **templater-obsidian** | Template engine — populates daily notes and wiki templates | Yes |
| **calendar** | Calendar sidebar — quick access to daily notes by date | Recommended |
| **table-editor-obsidian** | Markdown table editing — makes table-heavy notes easier to edit | Recommended |
| **media-extended** | Embedded media player — for video/audio notes and transcripts | Optional |

Registered in `.obsidian/community-plugins.json`:
```json
[
  "calendar",
  "obsidian-git",
  "dataview",
  "templater-obsidian",
  "table-editor-obsidian",
  "media-extended"
]
```

---

## Obsidian Git — Configuration

**File:** `.obsidian/plugins/obsidian-git/data.json`

This is the most critical plugin. It handles all git operations automatically
so you never lose vault changes.

### Key Settings

| Setting | Value | What it does |
|---------|-------|-------------|
| `autoSaveInterval` | `10` | Auto-commit every 10 minutes |
| `autoPushInterval` | `10` | Auto-push every 10 minutes (must match commit interval) |
| `autoPullInterval` | `10` | Auto-pull every 10 minutes (catches remote changes) |
| `autoPullOnBoot` | `true` | Pull latest on Obsidian startup |
| `autoBackupAfterFileChange` | `true` | Trigger backup when any file changes (not just on timer) |
| `pullBeforePush` | `true` | Always pull before push to avoid conflicts |
| `syncMethod` | `"merge"` | Use merge (not rebase) for conflict resolution |
| `commitMessage` | `"vault backup: {{date}}"` | Manual commit message format |
| `autoCommitMessage` | `"vault backup: {{date}}"` | Auto-commit message format |
| `commitDateFormat` | `"YYYY-MM-DD HH:mm:ss"` | Timestamp format in commit messages |

### Common Pitfalls

- **`autoPushInterval: 0` disables auto-push entirely.** Commits accumulate
  locally until you push manually. Always set this to match `autoSaveInterval`.
- **After editing `data.json` via CLI**, reload the plugin in Obsidian:
  `Settings → Community Plugins → Obsidian Git → Toggle off/on` (or restart Obsidian).
- **SSH key required.** The plugin uses git over SSH. Ensure `~/.ssh/` has a key
  registered with GitHub and `ssh-agent` is running.
- **Merge conflicts:** If auto-pull creates a conflict, Obsidian Git shows a
  notification. Resolve in terminal: `cd ~/second-brain && git mergetool`.

### Full Reference Config

```json
{
  "commitMessage": "vault backup: {{date}}",
  "autoCommitMessage": "vault backup: {{date}}",
  "commitDateFormat": "YYYY-MM-DD HH:mm:ss",
  "autoSaveInterval": 10,
  "autoPushInterval": 10,
  "autoPullInterval": 10,
  "autoPullOnBoot": true,
  "autoBackupAfterFileChange": true,
  "pullBeforePush": true,
  "syncMethod": "merge",
  "disablePush": false,
  "showStatusBar": true,
  "showBranchStatusBar": true,
  "refreshSourceControl": true,
  "refreshSourceControlTimer": 7000,
  "showErrorNotices": true
}
```

Settings not listed above can remain at their defaults.

---

## Daily Notes

**File:** `.obsidian/daily-notes.json`

```json
{
  "folder": "D.DAILY",
  "template": "A.DIVA/templates/daily"
}
```

- Notes go to `D.DAILY/` (flat, one file per day: `YYYY-MM-DD.md`)
- Template lives at `A.DIVA/templates/daily.md`
- The Calendar plugin reads this config — clicking a date creates/opens the daily note

---

## Templates

**File:** `.obsidian/templates.json`

```json
{
  "folder": "A.DIVA/templates"
}
```

Core templates are stored in `A.DIVA/templates/`:
- `daily.md` — daily note scaffold (used by Daily Notes + Calendar)
- Wiki note templates (`wiki-concept.md`, `wiki-person.md`, etc.) — used by `/reduce` and `/file-note`

Templater (`templater-obsidian`) is the template engine. It supports
dynamic content (dates, frontmatter generation) beyond what core Templates offers.

---

## Interaction with Knowledge Engine

The Knowledge Engine plugin (`knowledge-claude`) writes to the vault via CLI
(`git add + commit + push`), not through Obsidian Git. The two coexist safely:

| Actor | Writes via | Commits via | Pushes via |
|-------|-----------|-------------|-----------|
| **User (Obsidian)** | Obsidian editor | Obsidian Git plugin (auto, 10 min) | Obsidian Git plugin (auto, 10 min) |
| **Claude (CLI)** | `Write`/`Edit` tools | `vault-commit.sh` script | `vault-commit.sh` script |

**Conflict avoidance:** Obsidian Git's `pullBeforePush: true` and `autoPullOnBoot: true`
ensure it always pulls before pushing. Claude's `vault-commit.sh` also pulls before pushing.
Both use merge strategy, not rebase.

---

## Setup Checklist

Use this when setting up a new machine or verifying an existing setup:

- [ ] Vault cloned to `~/second-brain/` (or `$VAULT_ROOT`)
- [ ] SSH key configured for GitHub (`ssh -T git@github.com` works)
- [ ] Obsidian installed and vault opened
- [ ] Community plugins enabled (toggle in settings)
- [ ] All 6 plugins installed: `obsidian-git`, `dataview`, `templater-obsidian`, `calendar`, `table-editor-obsidian`, `media-extended`
- [ ] Obsidian Git configured with `autoPushInterval: 10` (not 0!)
- [ ] Daily notes folder set to `D.DAILY`
- [ ] Templates folder set to `A.DIVA/templates`
- [ ] Verify auto-sync: edit a note, wait 10 min, check `git log` on another machine

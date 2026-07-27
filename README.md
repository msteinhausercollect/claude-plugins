# Fanatics Collectibles — Claude Plugins

Internal Claude plugins for Fanatics Collectibles. Currently one plugin:

- **fan-deck-builder** — two skills over the Airtable slide catalog (~4,969 slides / 145 decks):
  - `slide-search` — "do we have slides on X?" → top matches with SharePoint links to the source decks
  - `deck-builder` — assemble a full on-brand .pptx from real catalog slides (retrieval ladder, brand format spec, slide manifest)

These are the same capabilities as Agent0's deck-builder skill (fanatics-live/agentskills PR #378), adapted to run in Claude Code / Claude Desktop / Cowork for anyone who doesn't use Agent0.

## Install (Claude Code / Cowork)

The repo is public — no GitHub account or auth needed:

```
/plugin marketplace add msteinhausercollect/claude-plugins
/plugin install fan-deck-builder@fanatics-collectibles
```

To try it directly from this local folder without a git repo:

```
/plugin marketplace add "/path/to/claude-plugins"
/plugin install fan-deck-builder@fanatics-collectibles
```

## Prerequisite: Airtable access

The skills read the slide catalog in Airtable (base `appFMMGAw98cxrGHz`). Each user needs ONE of:

1. **Airtable MCP connector** (easiest — claude.ai → Settings → Connectors → Airtable, sign in with an account that has access to the "Slide Catalog" base), or
2. **A read-only personal access token**: create a PAT at airtable.com/create/tokens with scope `data.records:read` on the base, then either export it as `AIRTABLE_PAT` or save it to `~/.config/fanatics-collectibles/airtable_token.txt` (chmod 600).

Ask the catalog owner for base access if you don't have it.

## Optional: native slide copying

The deck-builder produces the best output when it can copy native slides from the source decks. If you have the `SharePoint_Decks` folder synced locally via OneDrive, the skill will use it; otherwise it falls back to thumbnail placeholders and flags them in the manifest.

## Company-wide rollout options

- **This repo** (current): public, so anyone installs with the two commands above — the skills are inert without Airtable access, so nothing sensitive lives here. Transfer ownership before the owner leaves — see PUBLISHING.md.
- **Move into the fanatics-live org later**: transfer the repo (Settings → Transfer ownership) for org-owned durability; a Claude for Work admin can then auto-enable it for everyone (`extraKnownMarketplaces` + `enabledPlugins` in managed settings).
- **Claude in Slack (Claude Tag)**: an admin can register this repo as a skills repo at claude.ai/admin-settings → Claude Tag → Plugins, making the skills available in Slack channels.

## Maintenance

The skill content mirrors `Agent0_DeckBuilder_Spec_v2.md` (kept with the project files in the team's shared drive) and the Agent0 skill in fanatics-live/agentskills. When the spec changes, update both. Catalog schema changes (new fields, retired fields) land via the weekly `Agent0_Catalog_Sync` pipeline — keep the field tables in the two SKILL.md files in sync with the Airtable schema.

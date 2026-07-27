# Hosting, access, and ownership

This plugin lives in its own public GitHub repository:

**https://github.com/msteinhausercollect/claude-plugins**

Because it is public, anyone can install with no GitHub account or setup:

```
/plugin marketplace add msteinhausercollect/claude-plugins
/plugin install fan-deck-builder@fanatics-collectibles
```

The skills are useless without access to the private Airtable catalog and a
token, so the public repo exposes instructions, not data — no slides, no
credentials, no deck content live here. Keep it that way: never commit tokens,
slide exports, or SharePoint URLs.

## Transferring ownership (do this before the owner leaves)

A personal-account repo should be handed off when its owner moves on. Transfers
are one dialog:

1. Repo → Settings → General → Danger Zone → **Transfer ownership**.
2. Type the new owner: a colleague's GitHub username, or the `fanatics-live`
   organization (org repos are the most durable home; transferring in requires
   the sender to have repo-create rights in the org, which members have).
3. The recipient accepts from their email. History is preserved and old clone
   URLs redirect, but tell users to re-run
   `/plugin marketplace add <new-owner>/claude-plugins` so installs track the
   new location.

Public visibility makes transfers painless — no collaborator lists to rebuild
and nobody loses install access during the move.

## If the repo is ever lost

Nothing is gone — this folder IS the repo (git history included). Recover from
any surviving copy (`Assouline/claude-plugins/` on the shared OneDrive, or
`claude-plugins.zip`):

```bash
cd "<path-to>/claude-plugins"
gh repo create <your-account-or-org>/claude-plugins --public --source . --push
```

## No GitHub at all? (fallback)

The skills also work as plain files — no repo required:

- Copy `fan-deck-builder/skills/deck-builder/` and `.../slide-search/` into
  `~/.claude/skills/` on any machine → Claude Code picks them up automatically.
- Or add this folder as a local marketplace:
  `/plugin marketplace add "/path/to/claude-plugins"` then install as above.
- For claude.ai web/desktop chat: zip a single skill folder and upload it under
  Settings → Capabilities.

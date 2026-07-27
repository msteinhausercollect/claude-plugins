---
name: slide-search
description: Search the Fanatics Collectibles slide catalog in Airtable and return matching slides with SharePoint links to the source decks. Use when a user asks to find, look up, or check whether slides exist on a topic, sport, partner, athlete, or brand — without building a full deck.
---

# Fanatics Collectibles — Slide Catalog Search

## Overview

Fanatics Collectibles maintains an Airtable catalog of ~4,969 slides across 145 presentation decks covering partnerships, marketing, sales, athlete deals, product launches, and more. This skill makes that library searchable: given a question, find the most relevant slides and return them with enough context (title, category, sport, summary, freshness) plus a clickable SharePoint link to open the original PowerPoint. The goal is reuse — surface existing assets so nobody rebuilds a slide that already exists.

If the request is actually "build me a deck" or "adapt deck X for Y", use the `deck-builder` skill instead. This skill is for lookup.

## Airtable Access

Read-only. In order of preference:

1. **Airtable MCP connector**: `search_records` / `list_records_for_table` on the base below; call `get_table_schema` before filtering select fields.
2. **Airtable REST API** with a read-only personal access token (`data.records:read`), from the `AIRTABLE_PAT` environment variable or `~/.config/fanatics-collectibles/airtable_token.txt`. Never echo the token.
3. **Neither**: tell the user Airtable access to base `appFMMGAw98cxrGHz` is required and stop.

## Data Sources

- **Base ID:** `appFMMGAw98cxrGHz`
- **Slides table:** `tblJQ1ddoKy2Zi2mM`
- **Decks table:** `tbl8bBuZoPg7g3dmb`

### Slides fields to USE

| Field | Description |
|---|---|
| Slide ID | Unique identifier, `SLD-XXX-NN` |
| Deck ID | Parent deck, `DECK-XXX` |
| Title Text | Slide headline (plain text) |
| Category | One of 8 top-level categories |
| Subcategory | Topic within category (51 values) |
| Tags (Multi) | 147 filterable tags — hasAnyOf/hasAllOf |
| Sport(s) | e.g. Football (NFL), Basketball (NBA), Multi-Sport |
| Key Figures | Athletes, brands, orgs featured |
| Summary | ~160-char description |
| Body Text | Full extracted slide text — best field for keyword search |
| Data As Of | Freshness date of the slide's stats |
| Source File Name | Original deck filename |
| Dupe Group / Dupe Canonical | Near-duplicate cluster id + preferred member |

**Deprecated — do NOT use:** `Title`, `Tags`, `Confidential?` (mistyped legacy fields; `Confidential?` holds filenames), `In Library`.

### Decks fields

| Field | Description |
|---|---|
| Deck ID | Unique deck identifier |
| SharePoint Link | Direct URL to the source PowerPoint file |

## Instructions

1. Parse the query into search terms: sport, athlete/brand names, category, topic keywords.
2. Search down this ladder, combining levels when useful:
   - Explicit `SLD-`/`DECK-` ID → fetch directly. If it doesn't exist, say so and offer the nearest real matches — never pretend it exists.
   - Category/Subcategory for clean topical asks.
   - Tags (Multi) hasAnyOf for concrete entities (sport, partner, product line).
   - Summary + Body Text keyword search for anything conceptual — search the user's words AND synonyms ("keeping hobbyists engaged" → also "collector retention", "loyalty", "engagement").
   - Key Figures for named athletes, brands, orgs.
3. **Collapse duplicates:** when multiple hits share a `Dupe Group`, show only the `Dupe Canonical` member and note "N near-identical copies exist in older decks."
4. **Prefer fresh:** when equivalent slides differ, rank the newest `Data As Of` / newest deck first; flag stats older than 12 months.
5. Look up each result's `SharePoint Link` from the Decks table via its Deck ID.
6. Return the top 5 most relevant results (group slides from the same deck together). If nothing matches, say so honestly and suggest adjacent categories or a refined query — do not pad with tangential slides.
7. If the query is too vague to search, ask ONE clarifying question first.

## Output Format

```
Here are the most relevant slides I found:

**1. [Title Text]** (SLD-XXX-NN)
Category: [Category] > [Subcategory] · Sport: [Sport(s)]
Summary: [Summary]
Data as of: [Data As Of, if a stat is involved]
[Open in SharePoint →](SharePoint URL)

**2. …**
```

## Notes

- All catalog content is company-confidential by policy — do not filter results on `Confidential Flag`, but remind the requester that material is internal-only whenever they mention sharing it outside the company.
- Always include the SharePoint link so users can open the source file directly.
- Slide thumbnails exist as attachments if the user wants a visual preview.

# Public Goods Database Design

This document describes the implementation track. Teaching notes and unresolved
discussion live in `docs/learning-room.md`.

## Direction

The database should become reusable public infrastructure for Chinese-language
public goods knowledge. The Telegram agent is one consumer, not the owner of the
data model.

Initial scope:

- Seed one representative case from each existing GCC project category.
- Preserve compatibility with the existing `projects.yaml` knowledge base.
- Define schema fields for future detailed application imports.
- Define schema fields for future committee voting record imports.
- Define snapshot metadata so each project can later point to immutable source
  material.

Out of scope for this first step:

- Importing all 67 projects.
- Publishing private applications or committee records.
- Fully automating grant review.
- Replacing the current `pre_screen()` scoring logic.

## Data Layers

### 1. Public Case Record

This is the stable public-facing database record: name, category, amount,
summary, why funded, region, tags, links, and source URLs.

### 2. Source Snapshots

Snapshots are point-in-time references to source material. A snapshot can point
to a public web page, a private application, an exported PDF, a vote record, or a
future content-addressed archive.

The schema reserves fields for:

- `snapshot_id`
- `captured_at`
- `source_type`
- `storage_uri`
- `source_url`
- `checksum`
- `access_level`

### 3. Grant Application

Applications are modeled as linked evidence, not copied into the public database
by default. A case can say that an application exists, whether it is public,
private, or redacted, and where an authorized system can find it later.

### 4. Voting Record

Voting records are also modeled as linked evidence. The schema supports public
aggregate records now and can later support committee-level records if GCC
chooses to publish or internally expose them.

### 5. AI Screening Context

The bot should retrieve only the fields that are allowed for screening. This
prevents private applications and voting notes from accidentally becoming prompt
material.

## Design Principle

Each case should separate four things:

- What happened: public factual record.
- Why it was funded: GCC's reason and public goods interpretation.
- What evidence supports it: source URLs, snapshots, applications, votes.
- What AI may use: concise retrieval text and allowed screening dimensions.

## Migration Plan

1. Validate the new seed file manually and with YAML parsing.
2. Add a small loader for the new case format.
3. Update `pre_screen()` to retrieve similar cases from the case database.
4. Add semantic search after the schema is stable.
5. Import the remaining projects category by category.
6. Add application and vote snapshots once access and redaction rules are clear.


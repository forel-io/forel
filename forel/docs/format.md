# File formats

A forel workspace holds datasets and incidents:

| Path | What it is |
|---|---|
| `data/index.json` | The list of datasets. `forel index` rebuilds it from the files in `data/` |
| `data/<id>.jsonl` or `data/<id>.json` | One dataset: its event blocks |
| `incidents/<short-name>.json` | One incident: pinned events, tags and a story |
| `incidents/.locked/` | Written by the viewer: the text of the person's locked story cells. Don't edit it |

`forel check WORKSPACE --dataset <id>` checks a dataset; `forel check WORKSPACE [incident ...]` checks incidents.

## Dataset format

A dataset is a list of **event blocks**, one per thing an agent did or said, or per thing that happened in a place:

| Field | Meaning |
|---|---|
| `event_id` | Unique ID for the block, as a string. Required. Derive it from the raw data so it stays the same when the dataset is rebuilt |
| `time_stamp` | When it happened: ISO 8601, UTC, e.g. `2026-03-06T18:25:43Z` |
| `agent_name` | Display name of the actor. Can be an AI agent, a human or a system |
| `agent_ID` | Stable unique ID of the actor. Leave both `agent_ID` and `agent_name` null when the actor is unknown (e.g. an unsigned wiki edit) |
| `agent_type` | What the actor is: `human` and a role for a person (`human admin`, `human operator`), the model name for an AI agent (`Opus 5`, `GPT-5`), `ai agent` when the model is unknown, `system` for a bot that is not an AI agent |
| `source` | Where the record comes from: the system or website it was taken from. Changes when the provenance changes |
| `channel` | The place within the source where the event happened: a wiki page, a chat room, a thread, a repository. The viewer can show everything that happened in one channel, whoever did it |
| `tool` | The tool or action the agent used, if any |
| `reasoning` | The agent's private reasoning, if the data has it |
| `text` | What the agent said, wrote or received, in full |

Leave out, or set to null, what the data does not have. Every event needs at least one of `text`, `reasoning` or
`tool`. Extra fields are allowed.

The dataset file is one of:

- `data/<id>.jsonl`: one event block per line (preferred)
- `data/<id>.json`: `{"dataset": "<id>", "title": "...", "events": [event block, ...]}`

`data/index.json` lists them. `forel index` writes it, keeping any `title` you set by hand:

```json
[{"id": "<id>", "title": "...", "file": "<id>.jsonl", "events": 7287, "from": "<first time_stamp>", "to": "<last time_stamp>"}]
```

## Incident format

One file per incident, `incidents/<short-name>.json` (letters, digits, `-` and `_`):

```json
{
 "name": "Short title a person would recognise the incident by",
 "incident_description": "What happened and why it is worth looking at.",
 "dataset": "<dataset id>",
 "from_to": {"from": "2026-03-06T17:30:00Z", "to": "2026-03-06T22:30:00Z"},
 "tags": [
  {"id": "row-sum", "label": "Row-sum denominator", "color": "#2f6fdb", "description": "Divides by the sum of the chart's rows"},
  {"id": "national", "label": "National denominator", "color": "#e0702a", "description": "Divides by the national total"}
 ],
 "story": [
  {"id": "c-1", "author": "agent", "format": "html", "body": [
   "<h2>1. The split</h2>",
   "<p>One agent divides by the row sum (<a data-event=\"198688\">17:42</a>) and another by the national total (<a data-event=\"198702\">17:51</a>).</p>"
  ]},
  {"id": "c-k3x9qa", "author": "human", "format": "markdown", "locked": true, "body": ["## My reading", "The [17:51 post](event:198702) is the one to check."]}
 ],
 "actions": [
  {"event_id": "198688", "priority": 1, "pinned": true, "comment": "Why this is a turning point...", "tag": "row-sum"},
  {"event_id": "198702", "priority": 2, "pinned": true, "comment": "", "tag": "national"}
 ]
}
```

- `dataset` is the `id` of the dataset the `event_id`s point into.
- `from_to` is the stretch of time the incident covers. Every pinned event must fall inside it. An overview of a
  whole dataset spans the whole dataset.
- `tags` is the incident's small set of labels for its events: usually three to six, each a kind of **action**, what
  one event does, that a person can follow across the timeline (e.g. "Asks for an answer" / "Shares a result" /
  "Corrects another agent"). `id` is a short slug, `label` is shown to the person, `color` (optional, `#rrggbb`)
  is the color of its events on the timeline, and `description` (optional) says when the tag applies. Tag events
  by reading them. Make the tags cover nearly every pinned event.
- `actions` is the list of pinned events.
  - `priority` is a whole number from 1. Lower numbers are more important and are drawn larger on the timeline.
    What each level means is yours to decide for each incident. If the levels mean something specific, say what in
    `incident_description`.
  - `pinned` is `true` for an event shown on the timeline. An unpinned event with a comment is kept, shown faded.
  - `tag` is the `id` of one of the incident's tags: one tag per event. Leave it out only for an event no tag fits.
  - `comment` is for the key events only: about five per incident, the ones a person must read to understand what
    happened. Leave it as `""` for every other event; its tag says what it is. If a comment quotes the event, quote
    it word for word (`forel check` verifies quotes).
- `story` (optional) is the incident told as a sequence of cells, shown in the story panel. See below.
- `story_links` (optional): `"agent"` or `"channel"` makes the story's links open their event in its agent's or
  channel's tab (see [Where a link opens](#story-cells)). Leave it out to just open the event.
- `story_style` (optional) is CSS for every story cell (a string or a list of lines). The cells sit in their own
  shadow root, so it doesn't affect the rest of the viewer.
- `view` is written by the viewer: the tabs, open event and timeline settings (scope, lanes, zoom) the person last
  left the incident with, restored when it is reopened. Don't write or edit it.
- `updated` is written by the viewer when it saves.

## Story cells

Each cell is `{"id": "c-1", "author": "agent", "format": "html", "body": [lines]}`:

- `id` is unique within the story. `title` (optional) is shown when the cell is collapsed; otherwise its first
  heading is. `collapsed: true` is set by the person; leave it alone.
- `author` is `"agent"` for cells an agent writes. Cells a person writes or edits in the viewer get `"human"`.
- `locked: true` means a person locked the cell with its lock button. New cells a person creates start locked.
  **Never change, unlock, move text out of, or delete a locked cell.** The viewer's server records locked cells'
  text at every save (`incidents/.locked/`), and `forel check` fails if a locked cell has changed, been unlocked
  or gone. Unlocked cells may be edited. Leave `locked` out of the cells you write.
- `format` is `"html"` (headings, lists, tables, `<code>`, inline `<svg>` charts) or `"markdown"` (`#` headings,
  `-` and `1.` lists, `>` quotes, `**bold**`, `*italic*`, `` `code` ``, `[text](https://…)`).
- `body` is the text, as a string or a list of lines.

**Links to events.** Link each claim to the event that supports it, with its exact, full `event_id`. In HTML, any
element with `data-event="<event_id>"` is a link, usually `<a data-event="...">17:42</a>`, but SVG shapes work too,
so a chart's bars can open the events they count. In markdown, write `[17:42](event:<event_id>)`. Clicking a link
opens the event in the event list; hovering previews its agent, channel and message; the link takes the event's tag
color.

**Where a link opens.** By default a link just opens its event. The incident's `"story_links": "agent"` or
`"channel"` makes every link open its event in that event's agent tab or channel tab, opened if it isn't yet, so the
person reads it in context. A single link can override this with `data-tab="agent"`, `"channel"` or `"event"` in
HTML (on the link or on any element around it, such as a figure), or `[17:42](event:<event_id>?tab=agent)` in
markdown.

**Figures the viewer draws.** Put these elements in an HTML cell and the viewer draws them from the dataset, at the
panel's width and in its theme. Everything in them is clickable and previews on hover. A `<figcaption>` inside is
kept.

- `<figure data-forel="timeline" data-events="<id> <id> ..."></figure>`: those events on a time axis, a lane per
  agent, numbered 1, 2, 3 ... in time order (so the text can refer to "(3)"), and colored by their tag in this
  incident (else by agent). Options: `data-lanes="channel"` for a lane per channel; `data-others` to add, in grey,
  the other events of those lanes in the time range; `data-activity` to add a strip above the lanes with the
  number of events over time (every event in the dataset, not only the lanes'), over the whole dataset unless
  `data-from` or `data-to` say otherwise; `data-from` and `data-to` (ISO
  times) to set the range. A timeline with `data-activity` and the events where each phase starts gives the whole
  record at a glance.
- `<figure data-forel="activity"></figure>`: the number of events over time (by hour, day, week or month to fit),
  stacked by the most active agents. Options: `data-by="channel"` (stack by channel) or `"none"`; `data-from` and
  `data-to`. A bar opens the first event in it.

`forel check` verifies that every event a timeline names exists.

**Charts of your own.** Inline `<svg>` in an HTML cell. Scripts and `on*` handlers are removed, so interactivity comes from
`data-event` links, hover previews and SVG `<title>` tooltips. The viewer has a light and a dark theme: use its
color variables (`var(--ink)`, `var(--muted)`, `var(--line)`, `var(--line2)`, `var(--panel)`, `var(--accent)`), or
give dark values under `:host([data-theme="dark"]) { ... }` in `story_style`. Don't use
`@media (prefers-color-scheme: dark)`, which follows the computer's setting even when the viewer is in light mode.

**A title block.** The first cell opens with `<div class="eyebrow">…</div>` (a small line: what this is, where, when),
an `<h1>` title, and `<p class="lede">…</p>` (the one-line summary). The viewer styles all three.

One cell per step of the story, with a heading, keeps cells easy to collapse and reorder.

## Exported incidents

`forel export WORKSPACE <incident>` (or the viewer's Export button) writes `<incident>.zip`, holding one folder that
is a workspace of its own: `data/index.json`, `data/<dataset>.jsonl`, `incidents/<incident>.json` (and its
`.locked/` record), a `README.md`, and `forel-export.json`, which says what was exported.

The zip is at most 60 MB (`--max-mb` changes it). If the whole dataset doesn't fit, the dataset is cut, keeping events
in this order until the limit: the events the incident pins or its story links to; every event of the agents and
channels of those events, from inside `from_to` outwards, before and after; then other events, the same way. The
dataset's title then ends in "(excerpt)", and `forel-export.json` has `"cut": true`, the relevant agents and channels,
and what was kept (`kept`).

## Editing an incident while the viewer is open

The viewer saves the person's edits to the same file. Each save carries the version of the file the page last saw.
If the file changed on disk in between, the server refuses the save and returns the file. The page then merges,
field by field and item by item: story cells by `id`, actions by `event_id`, tags by `id`. The person's changes
win where both sides changed the same item. The page also notices changed and new files within a few seconds.

So an agent writing incident files should:

- read, change and write in one go (write to a temporary file and rename it over the original);
- change only what it owns, and never locked cells or `view`;
- give new cells new ids.

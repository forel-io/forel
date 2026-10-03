# The swarm incident viewer (for an AI agent)

You are helping a person investigate what a swarm of AI agents did. This file describes the tool you will be
writing files for and the formats it requires. How you convert the data and how you find incidents is up to you.

## What the tool is for

When many agents act at once, the record is too large for a person to read. The tool splits the work:

1. **You go first.** You read the raw record, find incidents worth a person's attention, and pin the events that
   tell each incident's story.
2. **The person digs deeper.** They open your incident in the viewer, see the pinned events on a timeline, and
   read each one with the events before and after it. They pin more, unpin, change priorities, retag and comment.

Nobody starts from a blank timeline: your incidents are the way in.

## The tool folder

Everything is in the folder this file is in. Paths below are relative to it.

| Path | What it is |
|---|---|
| `index.html`, `serve.py` | The viewer and its server: `python3 serve.py` |
| `data/index.json` | The list of datasets |
| `data/<dataset>.json` or `.jsonl` | One dataset: its event blocks |
| `incidents/<short-name>.json` | One incident |
| `check_incidents.py` | Checks that a dataset or an incident file is in the right format |

## Dataset format

A dataset is a list of event blocks, one per thing an agent did or said:

| Field | Meaning |
|---|---|
| `event_id` | Unique ID for the block, as a string. Required |
| `time_stamp` | When it happened: ISO 8601, UTC, e.g. `2026-03-06T18:25:43Z` |
| `agent_name` | Display name of the actor. Can be an AI agent, a human or a system |
| `agent_ID` | Stable unique ID of the actor. Leave both `agent_ID` and `agent_name` null when the actor is unknown (e.g. an unsigned wiki edit) |
| `agent_type` | Open field: a model name, "human", or whatever the data says |
| `source` | Where it happened, if known: a server, chat room, wiki, package registry |
| `channel` | The place within the source where the event happened, if known: a wiki page, a chat room, a gem. The viewer can show everything that happened in one channel, whoever did it |
| `tool` | The tool the agent called, if any |
| `reasoning` | The agent's private reasoning, if the data has it |
| `text` | What the agent said, wrote or received |

Leave out, or set to null, what the data does not have. Extra fields are allowed; the viewer ignores them.

The dataset file is one of:

- `data/<id>.json`: `{"dataset": "<id>", "title": "...", "events": [event block, ...]}`
- `data/<id>.jsonl`: one event block per line

Then add the dataset to `data/index.json`, keeping the entries already there:

```json
{"id": "<id>", "title": "...", "file": "<id>.json", "events": 7287, "from": "<first time_stamp>", "to": "<last time_stamp>"}
```

`python3 check_incidents.py --dataset <id>` confirms the viewer can read it.

## Incident format

One file per incident, `incidents/<short-name>.json`:

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
   "<p>An agent divides by the row sum (<a data-event=\"198688\">17:42</a>) and another by the national total (<a data-event=\"198702\">17:51</a>).</p>"
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
- `from_to` is the stretch of time the incident covers. Every pinned event must fall inside it.
- `tags` is the incident's small set of labels for its events: usually 2 or 3, each a position or a kind of
  behaviour the person can follow across the timeline (e.g. "National denominator" vs "Row-sum denominator", or
  "Treats it as a real signal" / "Corrects or warns others" / "Plans or uses a signal"). `id` is a short slug,
  `label` is shown to the person, `color` (optional, `#rrggbb`) is the color of its events on the timeline, and
  `description` (optional) says when the tag applies. Make the tags cover nearly every pinned event.
- `actions` is the list of pinned events.
  - `priority` is a whole number from 1. Lower numbers are more important and are drawn larger on the timeline.
    What each level means is yours to decide for each incident. If the levels mean something specific, say what
    in `incident_description`.
  - `pinned` is `true` for an event shown on the timeline.
  - `tag` is the `id` of one of the incident's tags: one tag per event. Leave it out only for an event no tag fits.
  - `comment` is for the key events only: about 5 per incident, the ones a person must read to understand what
    happened. Leave it as `""` for every other event; its tag says what it is. If a comment quotes the event,
    quote it word for word.
- `story` (optional) is the incident told as a sequence of cells, shown in a panel on the right of the viewer. A
  person can collapse a cell to its title, move it up or down, and edit it as rich text. Each cell is
  `{"id": "c-1", "author": "agent", "format": "html", "body": [lines]}`:
  - `id` is unique within the story. `title` (optional) is shown when the cell is collapsed; otherwise its first
    heading is. `collapsed: true` is set by the person; leave it alone.
  - `author` is `"agent"` for cells you write; cells a person writes or edits in the viewer get `"human"`.
  - `locked: true` means a person locked the cell with its lock button; new cells a person creates start locked.
    **Never change, unlock, move text out of, or delete a locked cell.** The viewer's server records locked cells'
    text at every save (`incidents/.locked/`; don't edit that folder), and `check_incidents.py` fails if a locked cell
    has changed, been unlocked or gone. Unlocked cells (yours, or a person's they unlocked) you may edit. Leave
    `locked` out of the cells you write.
  - `format` is `"html"` for your cells (headings, lists, tables, `<code>`, inline `<svg>` charts) or `"markdown"`
    (`#` headings, `-` and `1.` lists, `>` quotes, `**bold**`, `*italic*`, `` `code` ``, `[text](https://…)`).
  - `body` is the text, as a string or a list of lines.
  - Link each claim to the event that supports it. Use exact, full `event_id`s. In HTML, any element with
    `data-event="<event_id>"` is a link, usually `<a data-event="...">17:42</a>`, but SVG shapes work too, so a
    chart's bars can open the events they count. In markdown, write `[17:42](event:<event_id>)`. Clicking a link opens
    the event on the left; hovering previews its agent, channel and message; the link takes the event's tag color.
  - One cell per step of the story, with a heading, keeps cells easy to collapse and reorder.
- `story_style` (optional) is CSS for every story cell (a string or a list of lines). The cells sit in their own
  shadow root, so it doesn't affect the rest of the viewer; scripts and `on*` handlers are removed. The viewer has a
  light and a dark theme: use its color variables (`var(--ink)`, `var(--muted)`, `var(--line)`, `var(--accent)`) so
  the story follows it, or give dark values under `:host([data-theme="dark"]) { ... }`. Don't use
  `@media (prefers-color-scheme: dark)`, which follows the computer's setting even when the viewer is in light mode.

`python3 check_incidents.py <short-name>` confirms that every `event_id` exists in the dataset, every pinned event
is inside `from_to`, every `tag` is defined in `tags`, any quoted phrase in a comment appears in its event,
every event the `story` links to exists, and no locked story cell has changed. It also prints how many events have a comment, how many carry each tag,
and how many links the story has.

## One rule

Do not overwrite or edit an existing incident file unless the person asks. Those files hold people's pins and
comments. Write new incidents as new files.

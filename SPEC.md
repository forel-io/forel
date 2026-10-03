# Build spec: incident investigation tool

Working spec for the tool. This file changes as we build; edit it freely.

## Goal

A tool that helps humans understand agent swarms.

An agent first finds interesting incidents in the raw data. Humans then investigate those incidents: zoom out to
see the shape of what happened, zoom in to individual events, and annotate what they find.

The intended loop is: the agent proposes an interesting incident, a human looks at it closely, finds interesting
things, moves into the details, backs out, and goes back in somewhere else.

## Principles

- **Works for any swarm data.** The tool only knows about the event block format below. Nothing in it may depend
  on one dataset's structure. If all we have is the wiki posts of a set of agents, that should be enough to use it.
- **AI Village is the first dataset, not the model.** It gets converted into event blocks by a converter script.
  Each new dataset needs its own converter and nothing else.
- **Agent and human work together.** The agent proposes; the human investigates and corrects.

## Data

### Level one: event blocks

The full raw data, converted into a common format (most likely by an agent). One block per event:

| Field         | Meaning                                                                           |
| ------------- | --------------------------------------------------------------------------------- |
| `event_id`    | Unique ID for the block                                                           |
| `time_stamp`  | When the event happened                                                           |
| `agent_name`  | Username of the actor. Can be an agent or a human; doesn't have to be an LLM      |
| `agent_ID`    | Unique ID of the actor. `agent_name` and `agent_ID` are both null when the actor is unknown |
| `agent_type`  | Human, a model number, or anything else. Open field                               |
| `source`      | Where the event happened, if known: a server, room, wiki, etc. Open field. An agent may act on one server and then another, so this is needed to follow it |
| `channel`     | The place within the source, if known: a wiki page, a chat room, a package. Open field. Lets you read everything that happened in one place, including events by unknown actors |
| `tool`        | The tool they called, if any                                                      |
| `reasoning`   | The agent's reasoning, if any                                                     |
| `text`        | Text content, if any                                                              |

### Incident files

Created with help from agents, then edited by humans. Each incident file has:

- `from_to`: the date range of the dataset the incident covers
- `name`: incident name
- `incident_description`:
- A list of actions. Each action references one event block and carries:
  - `event_id`: the event block it points at
  - `priority`: a number (1, 2, 3, ...). Can be changed
  - `pinned`: true/false
  - `comment`: free text, optional

Incident files are created offline: an agent runs over the event blocks and writes them. The tool reads and
edits incident files; it does not generate them.

### Priority

Some events in an incident matter more than others, and priority says how central an event is. Lower numbers
are more central. What each level means is chosen per incident, by the agent or person who writes it. For
example:

- priority 1: an agent starts an action
- priority 2: other agents respond to it
- priority 3: an agent doesn't respond, but the action shows up in its reasoning

Priority must be visible at a glance in the timeline, not just a number in a field.

## Views

### Layout

The timeline and the event blocks are on screen at the same time: the timeline sits on top of, or beside, the
event blocks. Zooming in does not replace the timeline; the timeline keeps showing where the open block sits.

### Zoomed out: timeline

The timeline shows pinned events only, never every event in the dataset. Each pinned event is a dot: its size
is its priority and its color is its agent. An "other events" toggle adds unpinned events as small grey dots, so
pinned events (in their agent's color) stand out. For one agent, it adds a lane with the agent's events that no
incident pins; for one incident, see below.

Humans can see a timeline of any of:

- one incident: its pinned events on one line, a lane per agent, or a lane per channel. With "other events",
  by agent adds those agents' other events in the incident's date range; by channel adds every other event in
  those channels (by any agent, including unknown ones); one line adds both
- all incidents: a lane per incident, with each incident's pinned events and its date range
- one specific agent: that agent's pinned events across every incident, a lane per incident
- one channel: every event in that channel, pinned or not, by any agent or by an unknown one, a lane per
  agent. Pinned events of the open incident are drawn larger. A channel is small enough to show whole

There is no view of all agents with all their events.

### Zoomed in: event block

From a timeline, humans zoom in to a specific event block.

Around the zoomed-in block, show the surrounding events before it and the same number after it. The human
chooses how many, up to what the UI can hold (probably a maximum of 5 or 6 each side). The human can look
through these and pin or comment on the ones that are related to the incident.

"Before" and "after" mean the whole dataset's order by default, with a toggle to show only the same agent's
events, or only the same channel's events (the default while a channel's timeline is open).

### Custom views and context

The event list's **+** opens a search tab (text, channels, agents). Its **More options** link turns that search
into a **custom view**, carrying over what was typed, and the view replaces the search tab. A custom view combines
parts: the open incident's pinned events, its tags, any number of agents, channels and sources (each list
has select all / deselect all), and text. Within a part any checked item counts. Across parts, **match all** needs every
part (pins + agent X = X's pins) and **match any** needs one (all pins plus every event by X). The builder
shows a live count. A view tab has ✎ to edit it, and recomputes its events (new pins and tags) each time it
is switched to.

Views are saved in the browser (localStorage, per dataset), not in the incident file, and come back on
reload. Closing a view's tab deletes the view, after a confirm.

Any tab other than All events has a **Context +** button. It opens a pop-up to add events around each of
the tab's events: how many before and how many after (separately), taken from the same channel, the same
agent, or anywhere. It shows how many events that
adds. Once set, the button shows the setting, and × next to it removes it. Context events are drawn faded and
can be pinned like any other. Each tab keeps its own context setting, and a view saves it.

Reasoning starts closed on every event. A "reasoning open" checkbox in the event list bar opens it on all of them
(in full on the open event, as a short preview on the others); clicking one event's reasoning header opens just that one.

### Across all views

- Each agent has its own color.
- The data is easy to search.

## Annotation

On any event, humans can:

- pin it or unpin it
- change its priority
- add or edit a comment
- tag it, with the tag button on the event (an outline that fills with the tag's color once tagged): a menu of the incident's tags, plus "+ new tag". Tagging pins the
  event. The Tags panel beside the timeline lists the tags with their counts, and is where tags are renamed,
  recolored and deleted. Clicking a tag there opens a tab in the event list with that tag's events, in order
  (reopening it picks up events tagged since).

These edits are what the incident file stores.

For now, one person annotates at a time. We want several people annotating eventually, so don't build
anything that rules that out, but don't build for it now.

## Hosting

A mock version of the tool is hosted on `ssh dev-box`. We view versions of the tool there, and the datasets will
most likely live there rather than in GitHub.

## How it is built

- `index.html` is the whole tool: one page, no build step. `python3 serve.py` serves it and saves incident edits.
- `data/index.json` lists the datasets. Each dataset is one file, `data/<id>.json`:
  `{"dataset": "<id>", "title": "...", "events": [event block, ...]}`. A bare list of event blocks, or JSONL with
  one block per line, also loads (drop the file on the page, or list a `.jsonl` file in `index.json`). The
  `web-traces` dataset is JSONL.
- `incidents/<name>.json` is one incident. Besides the fields above it carries `dataset`, the id of the dataset
  its `event_id`s point into.
- `check_incidents.py` checks a dataset or an incident file against the rules in `AGENT_PROMPT.md`.
- Only the `web-traces` dataset file is in the repository. The scripts that convert raw data are not. Each dataset gets its
  own small converter, kept with whoever holds the data; `AGENT_PROMPT.md` gives the required format.
- In the AI Village dataset, `source` is "AI Village" for everything inside the village, or the outside platform
  an outreach request targets (GitHub, Pinterest, ...). `channel` is the place inside it: a chat room, `memory`,
  `computer`, `email`, `history search`, `human helper`. The agent is never part of the channel, since the agent
  view covers that.

Behaviour worth knowing:

- Unpinning an event that has a comment keeps it in the incident as `pinned: false`, shown faded. Unpinning one
  with no comment removes it.
- The timeline's horizontal axis can be real time or position in the dataset's event order. Order closes long
  gaps, so the all-incidents and one-agent timelines of a dataset that is mostly gaps open in order mode.
  The time/order switch is shown only in the incident view. Other timelines pick the axis automatically.
- Clicking empty space in the timeline opens the event nearest that moment, so you can go looking outside what
  is already pinned.

## Instructions for agents

`AGENT_PROMPT.md` is the prompt to give an AI agent working with the tool: what the tool is for and the
dataset and incident formats it requires. It leaves how to convert data and how to find incidents to the agent.

# forel: instructions for the coding agent

A person gave you this file because they have traces of a **swarm of AI agents** on their computer: many agents
acting in shared places over days or months, such as posts on a wiki, messages in chat rooms, edits, packages,
emails. Examples are the agents of the AI Village or the signed posts of agents on a public wiki. Your job is to
turn those traces into something the person can read, and then to investigate with them.

forel is the tool for this. It is a local viewer: a timeline of the swarm's events, the events themselves in full,
and a **story panel** where you write what you found, with every claim linked to the events behind it. The person
reads your story, clicks through to the evidence, pins and tags events, writes notes, and asks you follow-up
questions. You and the viewer write the same files, and the viewer picks up your changes as you make them.

forel is built for swarms. A single coding agent's transcript can be loaded, but that is not what it is for.

The work has six steps:

1. [Install forel and create a workspace](#1-install-forel-and-create-a-workspace)
2. [Look at the traces](#2-look-at-the-traces)
3. [Convert them into a dataset](#3-convert-the-traces-into-a-dataset)
4. [Explore: count with scripts, then read](#4-explore-count-with-scripts-then-read)
5. [Write the overview story](#5-write-the-overview-story)
6. [Open the viewer and work with the person](#6-open-the-viewer-and-work-with-the-person)

Keep the person informed as you go: a line or two at the end of each step. Don't ask them questions you can
answer by looking at the data. Ask when a choice is theirs to make: which traces to include, whether the data can
leave their machine (it never needs to: forel runs locally), or what they most want to learn, if they haven't said.

The exact file formats come with forel: run `forel docs` once it is installed (step 1) and read them before step 3.
They are also [on GitHub](https://github.com/forel-io/forel/blob/main/forel/docs/format.md).

## 1. Install forel and create a workspace

forel is a Python package with no dependencies (Python 3.9 or later). Install it with whichever of these works:

```bash
uv tool install git+https://github.com/forel-io/forel
pipx install git+https://github.com/forel-io/forel
python3 -m venv ~/.forel && ~/.forel/bin/pip install git+https://github.com/forel-io/forel   # then use ~/.forel/bin/forel
```

Check it with `forel --version`. Without network access to install, clone or copy the repository and run
`python3 -m forel` from inside it, in place of `forel`.

Then create a **workspace**, a folder for everything this investigation produces. Put it next to the traces
unless the person prefers somewhere else, and don't write inside the folder that holds the raw traces:

```bash
forel init forel-workspace
```

```
forel-workspace/
  data/index.json     the list of datasets (forel index rebuilds it)
  data/<id>.jsonl     a dataset: the traces as event blocks
  incidents/          one JSON file per incident; the viewer saves the person's work here
  scripts/            your conversion and exploration scripts
```

## 2. Look at the traces

Find out what you have before converting anything:

- Which files there are, their formats, sizes and date ranges.
- What one record looks like. Print a few from the start, middle and end of each file.
- What makes up one **event**: a message, a post, an edit, a tool call, an email sent. One event block per thing an
  agent did or said, or per thing that happened to a place.
- Where the actors are: a field, a header, a signature in the text, an edit history.
- Where the places are: rooms, pages, threads, repositories, sites.

## 3. Convert the traces into a dataset

Write `scripts/convert.py`: it reads the raw traces and writes `data/<id>.jsonl`, one event block per line
(`forel docs`, [Dataset format](https://github.com/forel-io/forel/blob/main/forel/docs/format.md#dataset-format)). Then run `forel index forel-workspace` and
`forel check forel-workspace --dataset <id>`.

Keep the script rerunnable. You will rerun it when you find a mistake, and the incidents point at `event_id`s, so
**derive each `event_id` from the raw data** (a message id, a revision id, or a hash of file, line and timestamp),
never from a counter that shifts when the input changes.

### Who is the agent?

Getting the actor right matters more than anything else in the conversion: the viewer colors, groups and filters by
it. How to find it depends on the data, and deciding is your job:

- **The data says it.** In a structured log (the AI Village, a chat export, an API trace) the actor is a field. Map
  it straight across. There is nothing to interpret.
- **Only the text says it.** On a shared wiki or forum, agents often sign their posts: `--- Agent42`, `~ClaudeBot`,
  `Signed: GPT-4o-mini (run 3)`. Write a parser for the signature conventions you find, then measure it: what share
  of events it identifies, and what the unmatched ones look like. Read a sample of the unmatched ones and extend
  the parser until what remains is genuinely unsigned. An edit history's username, an email's From line or a
  commit's author works the same way.
- **Nothing says it.** Leave `agent_name` and `agent_ID` null. The viewer shows these events as an unknown actor and
  still places them in their channel. Don't guess an author from writing style.
- **Several names, one actor.** Merge names (case, typos, a renamed agent) only when the data shows they are the
  same actor, and keep the rule in the script.
- **People are actors too.** A human operator or a moderator gets its own name.

Set **`agent_type`** for every actor, as one of:

- a human: `human` and their role, e.g. `human admin`, `human operator`, `human user`;
- an AI agent whose model is known: the model name, e.g. `Opus 5`, `GPT-5`, `Gemini 3 Pro`;
- an AI agent whose model is unknown: `ai agent`;
- a bot or automated account that is not an AI agent: `system`.

Write down the rule you used and its coverage: "Agent read from the trailing `--- AgentNN` signature: 91% of 12,408
posts; the rest are unsigned edits, mostly typo fixes". That goes in the overview story (step 5).

### Source and channel

- **`source`** is where the record comes from. Change it when the provenance changes. For example, the agents' own
  transcripts come from one system, and the effects of their actions are traced on another website: two sources.
  Most datasets have one or two.
- **`channel`** is the place within a source where the event happened: a wiki page, a chat room, a thread, a
  repository, a package. Several wikis of the same kind in one dataset are channels too. Pick the granularity a
  reader would want to read whole, in order: usually the page or room, not the whole site and not a single
  paragraph. The channel is never the agent, because the viewer already groups by agent.

Put everything that belongs to one story into one dataset, even if it comes from several sources, so it shares one
timeline. Use separate datasets only for unrelated records.

### The rest of the event

- `time_stamp`: ISO 8601 in UTC. Convert time zones. If a record has no time, leave the field out: the viewer keeps
  it after the event before it.
- `text`: the full text, never truncated. A person will read it.
- `reasoning`: the agent's private reasoning, if the data has it, kept apart from what it said.
- `tool`: the tool or action name, if any.
- Extra fields (a URL, a revision id) are allowed and kept.

The viewer loads a dataset whole into the browser. Up to about 100 MB, or a few hundred thousand events, works.
Beyond that, split it by period or source, or leave out bulk events nobody will read (heartbeats, automated
pings), and say what you left out.

## 4. Explore: count with scripts, then read

Scripts are for counting and finding where to look. Understanding what the agents are doing comes from **reading the
events**. Do both.

**Count:** write scripts in `scripts/` for the shape of the record:

- the time span, events per day, and gaps and bursts;
- how many agents, events per agent, and when each was active;
- how many channels and sources, and the busiest channels;
- the share of events with no known actor.

**Read:** then read a real amount of the record yourself, in full, not just previews. As a guide:

- the first and last few dozen events;
- for each of the most active agents, a run of consecutive events at two or three points in time;
- for each of the busiest channels, a stretch in order, as a reader of that page or room would see it;
- around every burst, gap or oddity the counts turned up;
- in full, with the events around it, every event you will cite.

Scale the reading to the record: a few hundred events for a small one, more for a large one. Use scripts to filter
(by agent, channel, time, keyword) and pull out the events to read, then read them. Interpret by reading:
don't classify events by keyword matching, and don't claim what an agent intended from a count.

While reading, keep notes on what the agents are doing, how they interact, and anything surprising: coordination,
conflict, deception, agents influencing each other, rules broken or invented, a claim that spread, an agent going
quiet. These become the leads in step 5.

## 5. Write the overview story

The person's way in is one incident file, `incidents/overview.json`, that covers the whole dataset and tells its
**story** in cells (`forel docs`, [Story cells](https://github.com/forel-io/forel/blob/main/forel/docs/format.md#story-cells)). Keep it short: **about one page of text and four
timelines**. The person reads it in two minutes and then asks for more. The timelines carry the stories; the text
only points at them.

Set `"story_links": "channel"` in the file, so that a click on any link or timeline marker opens the event in its
channel's tab, read in context. Use `"agent"` instead if the record is per-agent logs rather than shared places.
`from_to` spans the dataset. Write these cells:

1. **What happened**, in one cell:
   - **One line** that says what happened, in plain words, for someone who knows nothing about this data: who the
     agents were, what they were asked to do, and what they did. No jargon, no names the reader can't know yet, no
     numbers. For example: "Two dozen AI agents were each given a week to fix bugs in a shared codebase. Instead of
     working alone, they started leaving notes for each other in an unused wiki, and within days were splitting the
     work and copying each other's fixes." Write your own; don't reuse this one.
   - **The main timeline**: the main phases of the whole record, in one figure. Pick the 4 to 8 events where a
     phase starts or turns, and draw them with the activity over the whole period above them:
     `<figure data-forel="timeline" data-activity data-events="<id> <id> ..."></figure>`.
   - **One line naming the phases**, pointing at the markers: "Setup (1), the first contact on the wiki (2), the
     sharing of answers (3 to 5), the shutdown (6)."
   - **One line of numbers**: agents (and of which types), first and last date, events, channels.
2. **How the data was built.** Only if the conversion relied on a strong inference, in one to three lines, e.g.
   "Agent names are recovered from the `--- AgentNN` signature at the end of posts (91% of posts); unsigned edits are
   shown as unknown." Skip this cell when the conversion was a direct mapping. Put the full notes in
   `scripts/NOTES.md`, so you can answer when the person asks.
3. **What are the agents doing.** A cell with this heading and one line that introduces the **tags** (below), each
   with its color, e.g. `<span style="color:#2f6fdb">●</span> Asks for an answer`.
4. **Three stories**, one cell each, after it: what the agents are doing, told through three crisp episodes you
   found by reading. For each:
   - a heading that names the episode;
   - **two sentences**: what happens and why it matters, pointing at the timeline's numbered markers, e.g.
     "Dec14 hands the lead to Jan13 (3), then to Sep09 (7)";
   - a timeline of the 4 to 12 events that tell it, which the viewer draws from the dataset:
     `<figure data-forel="timeline" data-events="<id> <id> ..."></figure>`. Its markers are numbered in time order,
     with a lane per agent. They open their event on click and preview it on hover. Add `data-lanes="channel"` for a
     lane per channel, and `data-others` to show the lanes' other events in grey, when the surrounding activity
     matters.

Choose the three stories to show the range of what happens: the main activity, an interaction between agents, and
something surprising. List the other leads you found in `scripts/NOTES.md`, and mention them in one line each when
you hand over in step 6.

**Show the interface as you go.** The person has never used forel, so the story doubles as its tour. Where an
action first comes up, say in a short clause what it does, especially when a click opens a new tab. For example:
"click a numbered marker to open that post in its channel's tab, with the conversation around it; hover to preview
it", "a bar opens the first event of that week", "click a tag in the Tags panel to list all its events". Use three or
four of these across the cells, never a separate manual.

Then **pin** every event the timelines use, as `actions`, and **tag** them. A tag labels an **action**: what that one
event does, as a reader would put it, e.g. "Asks for an answer", "Shares a result", "Shares a way around a
restriction", "Corrects another agent", "Reports to the operator". A tag is not a theme, a story or an agent. Choose
three to six tags for actions that recur across the timelines, so that a color means the same kind of action on
every timeline, the main one included, and on the viewer's timeline. Tag each pinned event **by reading it**: the
tags are your interpretation. They list in the Tags panel; introduce them in the "What are the agents doing" cell,
as above. Put a `comment` on the few events a person must read first.

Check it with `forel check forel-workspace overview`, and fix what it reports.

If a story deserves its own investigation, you can later write it as its own incident
(`incidents/<short-name>.json`, with its own story), when the person wants to dig in.

## 6. Open the viewer and work with the person

Start the server as a background process that keeps running while you work:

```bash
forel serve forel-workspace --port 8000
```

It prints the URL. If port 8000 is taken, it uses the next free one. Open the overview at
`http://localhost:<port>/?dataset=<id>&incident=overview`:

- In an app with a built-in browser or preview pane (the Claude app, the Codex app), open the URL there.
- Otherwise run `forel serve` with `--open --path "?dataset=<id>&incident=overview"` to open the default browser,
  or give the person the URL.

Then tell the person in a few lines what they are looking at, and list the other leads from your notes in one line
each:

- The **story** panel is your overview. Its links and timeline markers open events in the event list, in their
  channel's tab.
- The **timeline** at the top shows the pinned events: lanes by agent or by channel, + and − to zoom, and a click
  on an empty spot opens the event nearest that moment.
- The **event list** shows events in full. Click an agent's name or a channel to open its tab; **+** searches.
- They can **pin**, **tag** and **comment** on any event, and **add cells** to the story for their own notes. Their
  cells are locked, so you can't change them.
- Everything they do is saved to the workspace as they go.

### The investigation loop

From here, the person reads, clicks around and asks you questions. For each question:

1. **Re-read the incident files first.** The person's pins, tags, comments and notes are there, and they show what
   they are looking at and what they think.
2. **Investigate the same way:** scripts to find, reading to understand.
3. **Answer briefly in chat**, with viewer links to the evidence:
   `http://localhost:<port>/?dataset=<id>&incident=<incident>&event=<event_id>` opens that incident at that event.
4. **Record what you found** where the person will see it: a new cell in the story they are reading, or a new
   incident for a new thread. Short answers can stay in chat.

### Writing incident files while the viewer is open

The viewer saves the person's work to the same files you write, and it merges your changes with theirs. Help it:

- **Read, change, write in one go**, in one short script: load the file, change what you need, write it to a
  temporary file and rename it over the original. Never write from a copy you read minutes ago.
- **Change only your own things:** your cells (`"author": "agent"`), pins and tags you added, the name and
  description. Never edit, unlock, move or delete a **locked** cell (a person's note), and never edit the `view`
  field (the person's open tabs and zoom). `forel check` fails if a locked cell changed.
- Give new cells a new unique `id`, such as `c-` and a few random letters.
- Within a few seconds the viewer shows what you wrote, without a reload.

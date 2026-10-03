# Forel

**Make sense of the swarm.**

When many AI agents act together for days or months, posting on wikis, talking in chat rooms, editing pages and publishing packages, they leave behind thousands of messages. Somewhere in there are the moments that matter: a claim that spread, a check that everyone skipped, an agent quietly going along with the group. Finding them by reading is the hard part.

Forel helps you and your coding agent investigate. Your agent reads the record and writes you the story, with every claim linked to its evidence. You read it, check it in context, and lead the investigation from there.


https://github.com/user-attachments/assets/0c494dd4-39aa-4118-be00-7dfd13a2c793


## Why Forel

- **Your agent does the reading.** Give it one message and the path to your traces. It installs Forel, converts the data, reads through it, and writes an overview: who the agents are, what they're doing, and the incidents worth digging into.
- **Every claim links to its evidence.** The story reads like a case study, and each claim opens the exact message behind it, with the conversation around it.
- **You catch what the agent missed.** Agents miss things and misread messages. The timeline, the events in full, and views by agent, by channel or by search let you see what actually happened and point your agent the right way.
- **Your layer on top.** Pin events, set priorities, tag and comment. Write your own notes in the story and lock them, so your agent can't change them.
- **Any swarm data.** Chat logs, wiki edits, package registries, emails: if agents left traces, your agent can convert them. Forel only needs one simple event format.
- **Any agent.** Claude, GPT, or whichever coding agent you use, in a desktop app, in VS Code or in the terminal.
- **Local.** The viewer runs on your machine and your data stays there. Investigations are plain JSON files.
- **Shareable.** Export an investigation and its data as a small zip anyone can open, and share it on [forel.io](https://forel.io).

Forel is for AI safety researchers and anyone studying how agents behave together. It is built for swarms: many agents in shared places. A single coding agent's transcript can be loaded, but that is not what Forel is for.

## Quick start

Give your coding agent (Claude Code, Codex, ...) this message, with the path to your traces:

> Follow https://forel.io/onboarding.md to set up Forel on the agent traces in `<path/to/traces>`. If you can't fetch it, read https://github.com/forel-io/forel/blob/main/ONBOARDING.md, or `git clone https://github.com/forel-io/forel` and read `ONBOARDING.md`.

The agent will:

1. install Forel and create a workspace next to your traces;
2. convert the traces into a dataset, deciding how to identify each agent and how to split the record into sources and channels;
3. explore the data: statistics from scripts, and a good amount of reading of the events themselves;
4. write an **overview story**: the period, the agents and their activity, what the agents are doing, and the incidents worth digging into;
5. start the viewer locally and open it, in the app's browser pane or in your browser.

Then you investigate. Read the story, click through to the events, and ask the agent questions. It adds what it finds to the story while you work.

## See an example

The repository includes a finished investigation: public traces that agents left on wikis and RubyGems, with four incidents, each with its story, timeline, pins and tags.

```bash
git clone https://github.com/forel-io/forel && cd forel
python3 -m forel serve examples/web-traces --open
```

More investigations are on [forel.io](https://forel.io).

## Using Forel directly

```bash
pip install git+https://github.com/forel-io/forel   # or: uv tool install / pipx install
forel init my-workspace                             # data/, incidents/, scripts/
forel index my-workspace                            # list the datasets in data/
forel check my-workspace --dataset my-swarm         # is the dataset readable?
forel check my-workspace                            # are the incidents valid?
forel serve my-workspace --open                     # the viewer, at http://localhost:8000
forel export my-workspace overview                  # overview.zip: the incident and its data, to share
```

The server listens on localhost only. Incidents are plain JSON files in the workspace.

## The viewer

- **Timeline** (top): the pinned events of the open incident, in lanes by agent or by channel. Bigger dots are the more important events; "other events" adds everything else the agents did, in grey. Zoom with + and −, drag to pan, and click an empty spot to open the event nearest that moment.
- **Event list** (left): every event in full, with its agent, channel, tool and reasoning. Click an agent or a channel to open its tab, use **+** to search or build a custom view, and use **Context +** to show the events around each one.
- **Story** (right): the incident's story, in cells that link to events, with timelines and charts. Add cells for your notes; they are locked so the agent can't change them.
- **Tags** (beside the timeline): click a tag to follow one thread through the whole incident.
- On any event: **pin** it, set its **priority**, **tag** it, **comment** on it.

**Export** (top right) downloads the open incident as a zip: the incident file (story, tags, pins, notes) and its dataset, as a small workspace anyone can open with `forel serve`. The zip is at most 60 MB. If the whole dataset doesn't fit, it is cut down to the events the incident pins or links to, every event of the agents and channels involved over the incident's time range widened before and after as far as the limit allows, and then other agents' events nearest the incident. The zip's README says what was kept.

Your edits save to the workspace as you go. The open tabs and timeline settings are saved with each incident, and come back when you reopen it.

## Docs

- [ONBOARDING.md](ONBOARDING.md): the instructions your coding agent follows
- [forel/docs/format.md](forel/docs/format.md): the dataset and incident formats (`forel docs` prints it)

## License

MIT. See [LICENSE](LICENSE).

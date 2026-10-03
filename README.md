# forel

Read what a swarm of agents did.

When many AI agents act in shared places for days or months, posting on wikis, talking in chat rooms, editing
pages and publishing packages, the record is too large to read. forel splits the work. **Your coding agent** converts
the traces, reads through them and writes an overview story with every claim linked to its evidence. **You**
open that story in a local viewer, follow the links, look around the timeline, pin and tag events, take notes and
ask the agent follow-up questions.

forel is built for swarm traces, such as the [AI Village](https://theaidigest.org/village) record or agents' signed
posts on a shared wiki. It is not built for a single coding agent's transcript.

## Quick start

Give your coding agent (Claude Code, Codex, ...) this message, with the path to your traces:

> Follow https://raw.githubusercontent.com/forel-io/forel/main/ONBOARDING.md to set up forel on the agent traces in
> `<path/to/traces>`.

The agent will:

1. install forel and create a workspace next to your traces;
2. convert the traces into a dataset, deciding how to identify each agent and how to split the record into
   sources and channels;
3. explore the data: statistics from scripts, and a good amount of reading of the events themselves;
4. write an **overview story**: the period, the agents and their activity, what the agents are doing, and the
   phenomena worth digging into;
5. start the viewer locally and open it, in the app's browser pane or in your browser.

Then you investigate. Read the story, click through to the events, and ask the agent questions. It adds what it
finds to the story while you work.

## Using forel directly

```bash
pip install git+https://github.com/forel-io/forel   # or: uv tool install / pipx install
forel init my-workspace                             # data/, incidents/, scripts/
forel index my-workspace                            # list the datasets in data/
forel check my-workspace --dataset my-swarm         # is the dataset readable?
forel check my-workspace                            # are the incidents valid?
forel serve my-workspace --open                     # the viewer, at http://localhost:8000
forel export my-workspace overview                  # overview.zip: the incident and its data, to share
```

To see what a finished investigation looks like, clone the repository and open the example workspace: public
traces that agents left on wikis and RubyGems, with four investigated incidents.

```bash
git clone https://github.com/forel-io/forel && cd forel
python3 -m forel serve examples/web-traces --open
```

Everything stays on your machine. The server listens on localhost only, and incidents are plain JSON files in the
workspace.

## The viewer

- **Timeline** (top): the pinned events of the open incident, in lanes by agent or by channel. Zoom with + and −,
  drag to pan, and click an empty spot to open the event nearest that moment. "Other events" adds the unpinned ones
  in grey.
- **Event list** (left): every event in full, with its agent, channel, tool and reasoning. Click an agent or a
  channel to open its tab, use **+** to search, and use **Context +** to show the events around each one.
- **Story** (right): the incident's story, in cells that link to events. Add cells for your notes; they are locked
  so the agent can't change them.
- On any event: **pin** it, set its **priority**, **tag** it, **comment** on it.

**Export** (top right) downloads the open incident as a zip to share, for example on the community website: the
incident file (story, tags, pins, notes) and its dataset, as a small workspace anyone can open with `forel serve`.
The zip is at most 60 MB. If the whole dataset doesn't fit, it is cut down to the events the incident pins or links
to, every event of the agents and channels involved over the incident's time range widened before and after as far as
the limit allows, and then other agents' events nearest the incident. The zip's README says what was kept.

Your edits save to the workspace as you go. The open tabs and timeline settings are saved with each incident, and
come back when you reopen it.

## Docs

- [ONBOARDING.md](ONBOARDING.md): the instructions your coding agent follows
- [docs/format.md](docs/format.md): the dataset and incident formats

## License

MIT. See [LICENSE](LICENSE).

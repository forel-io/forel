# Swarm incident viewer

A tool for investigating what a swarm of AI agents did. An AI agent reads the raw record first and proposes
incidents, pinning the events that tell each story. A person then opens an incident, sees the pinned events on a
timeline, reads each one with the events around it, and pins, prioritises and comments.

```
python3 serve.py     # http://localhost:8000; incidents save to incidents/
```

- `index.html` is the whole tool: one page, no build step. `serve.py` serves it and saves incident edits.
- `incidents/` holds the incident files. `check_incidents.py` checks them, and datasets, against the required formats.
- `AGENT_PROMPT.md` is the prompt to give an AI agent: what the tool is for and the formats it requires.
- `SPEC.md` is the build spec, including the event block format every dataset uses.

## Datasets

`web-traces` is in this repository; 
`data/` and list it in `data/index.json`, or drop it on the page.

The incidents in `incidents/` are all on `web-traces`. Both datasets:

- `web-traces`: public traces that LLM agents left on wikis, RubyGems and URL shorteners.

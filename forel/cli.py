"""forel: read what a swarm of agents did.

    forel init [WORKSPACE]                 create a workspace: data/, incidents/, scripts/
    forel index [WORKSPACE]                rebuild data/index.json from the dataset files in data/
    forel check [WORKSPACE] [INCIDENT...]  check incident files (or --dataset ID: a dataset)
    forel serve [WORKSPACE]                serve the viewer at http://localhost:8000
    forel export [WORKSPACE] INCIDENT      zip an incident and its data to share (max 60 MB: data cut to fit)

WORKSPACE defaults to the current folder. Formats: https://github.com/forel-io/forel/blob/main/docs/format.md
"""
import argparse, json, os, sys

from . import __version__

WORKSPACE_README = """# forel workspace

- `data/`: datasets, one file each (`<id>.jsonl` or `<id>.json`), listed in `data/index.json` (`forel index` rebuilds it)
- `incidents/`: one JSON file per incident; the viewer saves people's pins, tags and notes here as they work
- `scripts/`: the scripts that converted the raw traces and explored them

`forel serve` opens the viewer on this folder. `forel check` checks the datasets and incidents.
Formats: https://github.com/forel-io/forel/blob/main/docs/format.md
"""


def cmd_init(a):
    ws = os.path.abspath(a.workspace)
    for d in ('data', 'incidents', 'scripts'):
        os.makedirs(os.path.join(ws, d), exist_ok=True)
    idx = os.path.join(ws, 'data', 'index.json')
    if not os.path.exists(idx):
        with open(idx, 'w', encoding='utf-8') as f:
            f.write('[]\n')
    readme = os.path.join(ws, 'README.md')
    if not os.path.exists(readme):
        with open(readme, 'w', encoding='utf-8') as f:
            f.write(WORKSPACE_README)
    print(f'forel workspace ready at {ws}')
    print('  put datasets in data/ (then run: forel index), incidents in incidents/')
    return 0


def read_events(path):
    with open(path, encoding='utf-8') as f:
        if path.endswith('.jsonl'):
            return None, [json.loads(line) for line in f if line.strip()]
        raw = json.load(f)
    return (None, raw) if isinstance(raw, list) else (raw.get('title'), raw.get('events') or [])


def cmd_index(a):
    """data/index.json from the files in data/: one entry per dataset file, keeping titles already set."""
    data = os.path.join(os.path.abspath(a.workspace), 'data')
    path = os.path.join(data, 'index.json')
    old = {}
    if os.path.exists(path):
        try:
            old = {d['id']: d for d in json.load(open(path, encoding='utf-8'))}
        except (ValueError, KeyError, TypeError):
            pass
    out = []
    for fn in sorted(os.listdir(data)):
        if fn == 'index.json' or not fn.endswith(('.json', '.jsonl')) or fn.startswith('.'):
            continue
        ds = fn.rsplit('.', 1)[0]
        try:
            title, events = read_events(os.path.join(data, fn))
        except ValueError as e:
            print(f'skipped {fn}: not valid JSON ({e})')
            continue
        times = sorted(str(e['time_stamp']) for e in events if isinstance(e, dict) and e.get('time_stamp'))
        prev = old.get(ds, {})
        out.append({'id': ds, 'title': prev.get('title') or title or ds, 'file': fn, 'events': len(events),
                    'from': times[0] if times else None, 'to': times[-1] if times else None})
        print(f'{ds}: {len(events):,} events, {out[-1]["from"]} → {out[-1]["to"]}')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f'wrote {path} ({len(out)} dataset{"" if len(out) == 1 else "s"})')
    return 0


def cmd_check(a):
    from . import check
    return check.main(os.path.abspath(a.workspace), a.incidents, [a.dataset] if a.dataset else [])


def cmd_serve(a):
    from . import server
    server.serve(a.workspace, a.host, a.port, a.open, a.path.lstrip('/'))
    return 0


def cmd_export(a):
    from . import export
    return export.main(a.workspace, a.incident, a.output, int(a.max_mb * 1_000_000))


def main(argv=None):
    ap = argparse.ArgumentParser(prog='forel', description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--version', action='version', version=f'forel {__version__}')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('init', help='create a workspace')
    p.add_argument('workspace', nargs='?', default='.')
    p.set_defaults(fn=cmd_init)
    p = sub.add_parser('index', help='rebuild data/index.json from the dataset files in data/')
    p.add_argument('workspace', nargs='?', default='.')
    p.set_defaults(fn=cmd_index)
    p = sub.add_parser('check', help='check incident files, or a dataset')
    p.add_argument('workspace', nargs='?', default='.')
    p.add_argument('incidents', nargs='*', help='incident ids (default: all)')
    p.add_argument('--dataset', help='check this dataset instead')
    p.set_defaults(fn=cmd_check)
    p = sub.add_parser('serve', help='serve the viewer on a workspace')
    p.add_argument('workspace', nargs='?', default='.')
    p.add_argument('--port', type=int, default=8000, help='first port to try (default 8000; the next free one is used)')
    p.add_argument('--host', default='127.0.0.1', help='default 127.0.0.1. Anyone who can reach the server can edit, so keep it local')
    p.add_argument('--open', action='store_true', help='open the viewer in the default browser')
    p.add_argument('--path', default='', help='page to open, e.g. "?dataset=my-swarm&incident=overview"')
    p.set_defaults(fn=cmd_serve)
    p = sub.add_parser('export', help='zip an incident and its data to share')
    p.add_argument('workspace', nargs='?', default='.')
    p.add_argument('incident', help='incident id (the file name in incidents/, without .json)')
    p.add_argument('-o', '--output', help='zip file to write (default: <incident>.zip)')
    p.add_argument('--max-mb', type=float, default=60, help='size limit of the zip in MB (default 60); a bigger dataset is cut '
                   'to the events of the incident\'s agents and channels around its time range')
    p.set_defaults(fn=cmd_export)
    a = ap.parse_args(argv)
    if a.cmd == 'check' and not os.path.isdir(a.workspace):
        a.incidents.insert(0, a.workspace); a.workspace = '.'  # `forel check overview`: incidents of the current folder
    return a.fn(a)


if __name__ == '__main__':
    sys.exit(main())

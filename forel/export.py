"""Export an incident as a zip to share: the incident file (story, tags, pins, notes) and the dataset it reads.

The zip holds one folder, a forel workspace of its own, so whoever gets it can unzip it and run `forel serve` on it:

    <incident>/README.md
    <incident>/forel-export.json          what was exported, and how the data was cut if it was
    <incident>/data/index.json
    <incident>/data/<dataset>.jsonl
    <incident>/incidents/<incident>.json
    <incident>/incidents/.locked/<incident>.json   (if the person locked cells)

If the zip with the whole dataset would be over the size limit (60 MB by default), the dataset is cut down to the
events that matter most for the incident, in this order, until the limit is reached:
  1. the events the incident pins or its story links to (always kept);
  2. every event of the agents and channels those events involve, starting inside the incident's time range and
     widening it before and after, as far as the limit allows;
  3. then other agents' events, the same way.
The events kept are written in the dataset's own order.
"""
import bisect, datetime, json, os, re, zipfile, zlib

from . import __version__
from .check import story_links

DEFAULT_LIMIT = 60_000_000  # bytes: the community website's upload limit
LEVEL = 6

README = """# {name}

An incident exported from [forel](https://github.com/forel-io/forel) on {date}.

{description}

To read it, install forel and open this folder:

```bash
pip install git+https://github.com/forel-io/forel
forel serve {folder} --open
```

{data_note}
"""


def parse_t(s):
    if not s:
        return None
    try:
        return datetime.datetime.fromisoformat(str(s).replace('Z', '+00:00')).timestamp()
    except ValueError:
        return None


def fmt_t(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def fmt_span(sec):
    if sec >= 2 * 86400:
        return f'{sec / 86400:.1f} days'
    if sec >= 2 * 3600:
        return f'{sec / 3600:.1f} hours'
    return f'{sec / 60:.0f} minutes'


def read_dataset(path):
    """[(line bytes, event)] in file order. A .jsonl keeps its lines as they are."""
    out = []
    if path.endswith('.jsonl'):
        with open(path, 'rb') as f:
            for line in f:
                if line.strip():
                    out.append((line.rstrip(b'\r\n') + b'\n', json.loads(line)))
        return out
    with open(path, encoding='utf-8') as f:
        raw = json.load(f)
    events = raw if isinstance(raw, list) else raw.get('events') or []
    return [((json.dumps(e, ensure_ascii=False) + '\n').encode(), e) for e in events]


def ratio_estimate(rows, sample=8_000_000):
    """How much the dataset compresses, from evenly spread chunks of it."""
    total = sum(len(b) for b, _ in rows)
    if not total:
        return 1.0
    step = max(1, len(rows) // 200)
    raw = bytearray()
    for i in range(0, len(rows), step):
        for b, _ in rows[i:i + max(1, step * sample // total)]:
            raw += b
        if len(raw) >= sample:
            break
    return len(zlib.compress(bytes(raw), LEVEL)) / max(1, len(raw))


def relevance(rows, inc):
    """The order to keep events in when the data must be cut, and what it is based on."""
    events = [e for _, e in rows]
    ids = [str(e.get('event_id')) for e in events]
    present = set(ids)
    refs = {str(a.get('event_id')) for a in inc.get('actions') or [] if isinstance(a, dict)}
    refs |= {str(x) for x in story_links(inc)}
    refs &= present
    agent = lambda e: e.get('agent_ID') or e.get('agent_name')
    chan = lambda e: (e.get('source'), e.get('channel')) if e.get('channel') else None
    ref_ev = [e for e, i in zip(events, ids) if i in refs]
    agents = {agent(e) for e in ref_ev} - {None}
    chans = {chan(e) for e in ref_ev} - {None}
    times = [parse_t(e.get('time_stamp')) for e in events]
    ref_times = sorted(t for t, i in zip(times, ids) if i in refs and t is not None)
    ft = inc.get('from_to') or {}
    lo, hi = parse_t(ft.get('from')), parse_t(ft.get('to'))
    if lo is None or hi is None:
        lo, hi = (ref_times[0], ref_times[-1]) if ref_times else (None, None)
    far = float('inf')

    def key(k):
        e, t = events[k], times[k]
        tier = 0 if ids[k] in refs else 1 if (agent(e) in agents or chan(e) in chans) else 2
        if t is None:
            return (tier, far, far)
        out = 0.0 if lo is None else max(lo - t, t - hi, 0.0)  # how far outside the incident's time range
        j = bisect.bisect_left(ref_times, t)
        near = min([abs(t - ref_times[x]) for x in (j - 1, j) if 0 <= x < len(ref_times)] or [far])
        return (tier, out, near)

    keys = [key(k) for k in range(len(events))]
    order = sorted(range(len(events)), key=keys.__getitem__)
    return order, keys, {'refs': len(refs), 'agents': sorted(map(str, agents)),
                         'channels': sorted(f'{s}/{c}' if s else str(c) for s, c in chans), 'from': lo, 'to': hi}


def coverage(keys, keep, basis):
    """In words: what a cut dataset holds, tier by tier."""
    lo, hi = basis['from'], basis['to']
    lines = []
    for tier, what in ((1, 'the relevant agents and channels'), (2, 'other agents and channels')):
        all_ = [k for k in range(len(keys)) if keys[k][0] == tier]
        kept = [k for k in all_ if k in keep]
        if not all_:
            continue
        if len(kept) == len(all_):
            lines.append(f'{what}: all {len(all_):,} events')
        elif not kept:
            lines.append(f'{what}: none of their {len(all_):,} events')
        else:
            margin = max(keys[k][1] for k in kept)
            if margin > 0 and lo is not None:
                lines.append(f'{what}: {len(kept):,} of {len(all_):,} events, everything from {fmt_t(lo - margin)} '
                             f'to {fmt_t(hi + margin)} (the incident\'s time range plus {fmt_span(margin)} before and after)')
            else:
                lines.append(f'{what}: {len(kept):,} of {len(all_):,} events, the ones nearest the incident\'s '
                             f'events, inside its time range')
    return lines


def write_zip(path, folder, files, data_name, data_rows):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=LEVEL) as z:
        for name, body in files.items():
            z.writestr(f'{folder}/{name}', body)
        info = zipfile.ZipInfo(f'{folder}/data/{data_name}', datetime.datetime.now().timetuple()[:6])
        info.compress_type = zipfile.ZIP_DEFLATED  # (zlib's default level, 6, as LEVEL)
        with z.open(info, 'w', force_zip64=True) as f:
            for b in data_rows:
                f.write(b)
    return os.path.getsize(path)


def export(workspace, incident, out, limit=DEFAULT_LIMIT, log=print):
    """Write the zip for incidents/<incident>.json to the path `out`. Returns the manifest (forel-export.json)."""
    ws = os.path.abspath(workspace)
    if not re.fullmatch(r'[\w-]+', incident):
        raise ValueError(f'not an incident name: {incident!r}')
    inc_path = os.path.join(ws, 'incidents', incident + '.json')
    if not os.path.isfile(inc_path):
        raise FileNotFoundError(f'no incident {incident} (looked for {inc_path})')
    with open(inc_path, 'rb') as f:
        inc_bytes = f.read()
    inc = json.loads(inc_bytes)
    ds_id = inc.get('dataset')
    with open(os.path.join(ws, 'data', 'index.json'), encoding='utf-8') as f:
        ds = next((d for d in json.load(f) if d.get('id') == ds_id), None)
    if not ds:
        raise FileNotFoundError(f'incident {incident} reads dataset {ds_id!r}, which is not in data/index.json')
    log(f'reading {ds["file"]}…')
    rows = read_dataset(os.path.join(ws, 'data', ds['file']))
    data_name = ds_id + '.jsonl'
    raw_size = sum(len(b) for b, _ in rows)

    files = {f'incidents/{incident}.json': inc_bytes}
    locked = os.path.join(ws, 'incidents', '.locked', incident + '.json')
    if os.path.isfile(locked):
        with open(locked, 'rb') as f:
            files[f'incidents/.locked/{incident}.json'] = f.read()

    def finish(keep, note, manifest):
        sel = [rows[k] for k in sorted(keep)] if keep is not None else rows
        times = sorted(str(e['time_stamp']) for _, e in sel if isinstance(e, dict) and e.get('time_stamp'))
        entry = {'id': ds_id, 'title': (ds.get('title') or ds_id) + (' (excerpt)' if keep is not None else ''),
                 'file': data_name, 'events': len(sel), 'from': times[0] if times else None, 'to': times[-1] if times else None}
        manifest.update(events=len(sel), dataset_events=len(rows))
        out_files = dict(files)
        out_files['data/index.json'] = json.dumps([entry], ensure_ascii=False, indent=1)
        out_files['forel-export.json'] = json.dumps(manifest, ensure_ascii=False, indent=1)
        out_files['README.md'] = README.format(name=inc.get('name') or incident, date=manifest['exported'][:10],
                                               description=inc.get('incident_description') or '', folder=incident, data_note=note)
        return write_zip(out, incident, out_files, data_name, (b for b, _ in sel)), manifest

    manifest = {'forel': __version__, 'exported': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
                'incident': incident, 'dataset': ds_id, 'limit_bytes': limit}
    ratio = ratio_estimate(rows)
    if raw_size * ratio < limit * 0.95:  # the whole dataset most likely fits
        size, m = finish(None, f'The data is the whole dataset `{ds_id}`: {len(rows):,} events.', dict(manifest, cut=False))
        if size <= limit:
            log(f'wrote {out} ({size / 1e6:.1f} MB, the whole dataset)')
            return dict(m, bytes=size)

    log(f'the whole dataset ({raw_size / 1e6:.0f} MB, about {raw_size * ratio / 1e6:.0f} MB zipped) is over '
        f'{limit / 1e6:.0f} MB: keeping the events that matter most for {incident}…')
    order, keys, basis = relevance(rows, inc)
    sizes = [len(rows[k][0]) for k in order]

    def build(target):  # keep events in order of relevance up to `target` raw bytes, and write the zip
        n, acc = 0, 0
        while n < len(order) and (acc + sizes[n] <= target or keys[order[n]][0] == 0):  # pinned/linked: always
            acc += sizes[n]; n += 1
        keep = set(order[:n])
        lines = coverage(keys, keep, basis)
        note = '\n'.join([
            f'The data is an excerpt of the dataset `{ds_id}`: {n:,} of its {len(rows):,} events, to fit in '
            f'{limit / 1e6:.0f} MB. It has the {basis["refs"]:,} events the incident pins or links to, and:', '', *('- ' + x for x in lines), '',
            f'The relevant agents are those of the incident\'s events ({len(basis["agents"])}); the relevant channels '
            f'are the places those events happened ({len(basis["channels"])}). forel-export.json lists them.'])
        m = dict(manifest, cut=True, kept=lines, agents=basis['agents'], channels=basis['channels'],
                 incident_range={'from': fmt_t(basis['from']), 'to': fmt_t(basis['to'])} if basis['from'] is not None else None)
        size, m = finish(keep, note, m)
        log(f'  {n:,} events: {size / 1e6:.1f} MB')
        return n, size, m, all(keys[k][0] == 0 for k in keep)

    # The zipped size of an excerpt is only known once written: aim from the compression ratio, then correct.
    target, best, last = limit / ratio * 0.97, None, None
    for _ in range(6):
        n, size, m, only_refs = last = build(target)
        if size <= limit:
            if not best or n > best[0]:
                best = (n, target)
            if size > limit * 0.93 or n == len(order):
                break
        elif only_refs:
            raise ValueError(f'the incident\'s own events alone take {size / 1e6:.1f} MB, over the {limit / 1e6:.0f} MB limit')
        target *= limit / size * 0.98
    if not best:
        raise ValueError(f'could not fit the data in {limit / 1e6:.0f} MB')
    if last[1] > limit or last[0] < best[0]:
        last = build(best[1])
    n, size, m, _ = last
    log(f'wrote {out} ({size / 1e6:.1f} MB, {n:,} of {len(rows):,} events)')
    return dict(m, bytes=size)


def main(workspace, incident, out=None, limit=DEFAULT_LIMIT):
    out = out or f'{incident}.zip'
    try:
        export(workspace, incident, out, limit)
    except (ValueError, FileNotFoundError) as e:
        print(f'forel export: {e}')
        return 1
    return 0

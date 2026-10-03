"""Check a workspace's datasets and incident files (formats: docs/format.md).

    forel check WORKSPACE                       # every incident file in incidents/
    forel check WORKSPACE overview ...          # just these incidents
    forel check WORKSPACE --dataset my-swarm    # a dataset: is it valid event blocks?

For an incident: every event_id exists in its dataset, every pinned event falls inside from_to, every tag an event
uses is defined in "tags" (one tag per event), and every quoted phrase in a comment appears word for word in that
event's text or reasoning. If the incident has a "story" (a list of cells), every cell is well formed, every event a cell links to
([text](event:<id>) in markdown, data-event="<id>" or href="#event=<id>" in HTML) exists in the dataset, and every
locked cell still has the text the viewer last saved for it (incidents/.locked/<name>.json). It also counts key events (those with a comment), events per tag and story links. Quotes are compared ignoring case,
runs of whitespace, markdown asterisks and curly-vs-straight quote marks.
For a dataset: it is listed in data/index.json, every event has a unique event_id, and timestamps parse. Events with
no agent (unknown actor) and the number of channels are counted.
Exits 1 if any check fails.
"""
import datetime, glob, json, os, re, sys

DATA, INCIDENTS = 'data', 'incidents'
_datasets = {}


def use_workspace(workspace):
    global DATA, INCIDENTS
    DATA, INCIDENTS = os.path.join(workspace, 'data'), os.path.join(workspace, 'incidents')
    _datasets.clear()


def load_events(dataset):
    """The dataset's event blocks, from the file data/index.json names for it (JSON or JSONL)."""
    index = json.load(open(os.path.join(DATA, 'index.json'), encoding='utf-8'))
    entry = next((d for d in index if d['id'] == dataset), None)
    if not entry:
        raise SystemExit(f'dataset "{dataset}" is not listed in data/index.json')
    with open(os.path.join(DATA, entry['file']), encoding='utf-8') as f:
        if entry['file'].endswith('.jsonl'):
            return [json.loads(line) for line in f if line.strip()]
        raw = json.load(f)
        return raw if isinstance(raw, list) else raw['events']


def events_of(dataset):
    if dataset not in _datasets:
        _datasets[dataset] = {str(e['event_id']): e for e in load_events(dataset)}
    return _datasets[dataset]


def norm(s):
    s = (s or '').replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"').replace('*', '')
    return re.sub(r'\s+', ' ', s).lower()


def check(path):
    inc = json.load(open(path, encoding='utf-8'))
    problems = []
    for key in ('name', 'incident_description', 'dataset', 'from_to', 'actions'):
        if key not in inc:
            problems.append(f'missing "{key}"')
    if problems:
        return inc, problems
    tags = inc.get('tags', [])
    if not isinstance(tags, list) or any(not isinstance(t, dict) or not t.get('id') or not t.get('label') for t in tags):
        problems.append('"tags" must be a list of {"id", "label"} objects')
        tags = []
    tag_ids = [t['id'] for t in tags]
    if len(set(tag_ids)) < len(tag_ids):
        problems.append('a tag id is defined twice')
    events = events_of(inc['dataset'])
    lo, hi = inc['from_to'].get('from', ''), inc['from_to'].get('to', '')
    seen = set()
    for a in inc['actions']:
        eid = str(a.get('event_id'))
        e = events.get(eid)
        if not e:
            problems.append(f'{eid}: not in dataset {inc["dataset"]}')
            continue
        if eid in seen:
            problems.append(f'{eid}: listed twice')
        seen.add(eid)
        if a.get('pinned', True) and not (lo[:19] <= (e.get('time_stamp') or '')[:19] <= hi[:19]):
            problems.append(f'{eid}: pinned event at {(e.get("time_stamp") or "no time")[:19]} is outside from_to')
        if 'tag' in a and a['tag'] not in tag_ids:
            problems.append(f'{eid}: tag {a["tag"]!r} is not defined in "tags" (one tag per event, as a string id)')
        if not isinstance(a.get('priority'), int) or a['priority'] < 1:
            problems.append(f'{eid}: priority must be a whole number from 1')
        hay = norm(e.get('text')) + ' ' + norm(e.get('reasoning'))
        for q in re.findall(r'"([^"]*)"', norm(a.get('comment'))):  # pair quote marks in order, then skip very short ones
            if len(q) >= 4 and q.strip(' .,…') not in hay:
                problems.append(f'{eid}: quoted phrase not found in the event: "{q}"')
    problems += check_story(inc, events, os.path.basename(path)[:-5])
    return inc, problems


def text_of(body):
    return '\n'.join(body) if isinstance(body, list) else str(body or '')


def story_cells(inc):
    """The story as cells. A story from before cells (one HTML string, or a list of lines) is one agent cell."""
    s = inc.get('story') or []
    if isinstance(s, str) or (isinstance(s, list) and s and all(isinstance(x, str) for x in s)):
        return [{'id': 'c-1', 'author': 'agent', 'format': 'html', 'body': s}]
    return s if isinstance(s, list) else []


def cell_links(c):
    body = text_of(c.get('body'))
    if c.get('format') == 'markdown':
        return re.findall(r'\]\(event:([^)\s]+)\)', body) + re.findall(r'data-event\s*=\s*["\']([^"\'\s>]+)', body)
    return re.findall(r'''(?:data-event\s*=\s*|href\s*=\s*["']?#event=)["']?([^"'\s>]+)''', body)


def story_links(inc):
    return [eid for c in story_cells(inc) if isinstance(c, dict) for eid in cell_links(c)]


def check_story(inc, events, name):
    problems, ids = [], set()
    s = inc.get('story')
    if s is not None and not isinstance(s, (str, list)):
        return ['"story" must be a list of cells']
    for k, c in enumerate(story_cells(inc)):
        where = f'story cell {k + 1}'
        if not isinstance(c, dict):
            problems.append(f'{where}: a cell must be an object {{"id", "author", "format", "body"}}')
            continue
        where += f' ({c.get("id")})'
        if not c.get('id') or c['id'] in ids:
            problems.append(f'{where}: needs an "id" no other cell has')
        ids.add(c.get('id'))
        if c.get('author') not in ('human', 'agent'):
            problems.append(f'{where}: "author" must be "human" or "agent"')
        if c.get('format') not in ('markdown', 'html'):
            problems.append(f'{where}: "format" must be "markdown" or "html"')
        if not isinstance(c.get('body', ''), (str, list)):
            problems.append(f'{where}: "body" must be text or a list of lines')
        for eid in cell_links(c):
            if eid not in events:
                problems.append(f'{where}: links to {eid}, which is not in dataset {inc["dataset"]}')
    style = inc.get('story_style')
    if style is not None and not (isinstance(style, str) or (isinstance(style, list) and all(isinstance(x, str) for x in style))):
        problems.append('"story_style" must be CSS text or a list of lines')
    # Locked cells (a person locks them in the viewer; new cells start locked): the viewer's server records their text
    # at every save (incidents/.locked/), and nothing else may change, unlock or remove them.
    lock = os.path.join(INCIDENTS, '.locked', name + '.json')
    if os.path.exists(lock):
        cells = {c.get('id'): c for c in story_cells(inc) if isinstance(c, dict)}
        for cid, rec in json.load(open(lock, encoding='utf-8')).items():
            c = cells.get(cid)
            if not c:
                problems.append(f'locked story cell {cid} is missing. Only a person may remove a locked cell, in the viewer')
            elif not c.get('locked', c.get('author') == 'human'):
                problems.append(f'locked story cell {cid} was unlocked outside the viewer. Only a person may unlock it, with its lock button')
            elif text_of(c.get('body')) != rec.get('body') or c.get('title') != rec.get('title'):
                problems.append(f'locked story cell {cid} was changed outside the viewer. Restore it: only a person may edit a locked cell')
    return problems


def check_dataset(dataset):
    events = load_events(dataset)
    problems, ids, undated, agents, unknown, channels = [], set(), 0, set(), 0, set()
    for n, e in enumerate(events):
        eid = e.get('event_id')
        if eid is None:
            problems.append(f'event {n}: no event_id')
        elif str(eid) in ids:
            problems.append(f'event {n}: event_id {eid} is used more than once')
        ids.add(str(eid))
        if e.get('agent_ID') or e.get('agent_name'):
            agents.add(e.get('agent_ID') or e.get('agent_name'))
        else:
            unknown += 1
        if e.get('channel'):
            channels.add(e['channel'])
        t = e.get('time_stamp')
        try:
            datetime.datetime.fromisoformat(str(t).replace('Z', '+00:00').replace(' ', 'T'))
        except ValueError:
            undated += 1
        if not (e.get('text') or e.get('reasoning') or e.get('tool')):
            problems.append(f'event {eid}: no text, reasoning or tool')
        if len(problems) >= 20:
            problems.append('... stopping after 20 problems')
            break
    times = sorted(str(e['time_stamp']) for e in events if e.get('time_stamp'))
    print(f'{"FAIL" if problems else "ok  "} dataset {dataset}: {len(events):,} events, {len(agents):,} agents, '
          f'{times[0][:10] if times else "?"} → {times[-1][:10] if times else "?"}'
          + (f', {unknown:,} with no agent' if unknown else '') + (f', {len(channels):,} channels' if channels else '')
          + (f', {undated} with no readable time_stamp (they are placed after the event before them)' if undated else ''))
    for p in problems:
        print('       ' + p)
    return not problems


def main(workspace, names=(), datasets=()):
    """Returns the exit code: 0 if every check passes."""
    use_workspace(workspace)
    if datasets:
        return 0 if all([check_dataset(d) for d in datasets]) else 1
    paths = [os.path.join(INCIDENTS, n + '.json') for n in names] or sorted(glob.glob(os.path.join(INCIDENTS, '*.json')))
    if not paths:
        print(f'no incident files in {INCIDENTS}')
    failed = 0
    for path in paths:
        inc, problems = check(path)
        pins = [a for a in inc.get('actions', []) if a.get('pinned', True)]
        by_p = {p: sum(1 for a in pins if a.get('priority') == p) for p in sorted({a.get('priority') for a in pins}, key=str)}
        key = sum(1 for a in pins if (a.get('comment') or '').strip())
        by_tag = {t.get('id'): sum(1 for a in pins if a.get('tag') == t.get('id')) for t in inc.get('tags') or [] if isinstance(t, dict)}
        untagged = sum(1 for a in pins if not a.get('tag'))
        print(f'{"FAIL" if problems else "ok  "} {os.path.basename(path)}: {len(pins)} pinned {by_p}, {key} with a comment'
              + (f', tags {by_tag}' if by_tag else '') + (f', {untagged} untagged' if by_tag and untagged else '')
              + (f', story: {len(story_cells(inc))} cells ({sum(1 for c in story_cells(inc) if isinstance(c, dict) and c.get("locked", c.get("author") == "human"))} locked), {len(story_links(inc))} event links' if inc.get('story') else ''))
        for p in problems:
            print('       ' + p)
        failed += bool(problems)
    return 1 if failed else 0

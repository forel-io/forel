"""Serve the incident viewer, and save incident files (incidents/).

    python3 serve.py                 # http://localhost:8000, opens your browser
    python3 serve.py --port 8765 --no-open
    python3 serve.py --host 0.0.0.0  # reachable from other machines (no login: anyone who can reach it can edit)

Same as `python3 -m http.server -d viewer`, plus:
  GET /incidents/index.json     a listing of every incident file (built on request)
  PUT /incidents/<name>.json    save one incident
JSON is gzipped on the way out, since dataset files are tens of MB.
Listens on 127.0.0.1 unless --host says otherwise. Incidents are plain JSON, so commit them like any other file.
"""
import argparse, functools, gzip, http.server, json, os, re, webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
INCIDENTS = os.path.join(HERE, 'incidents')
_gz = {}  # path -> (mtime, gzipped bytes)


class Handler(http.server.SimpleHTTPRequestHandler):
    def send_json(self, body):
        if 'gzip' in self.headers.get('Accept-Encoding', ''):
            body = gzip.compress(body, 5)
            encoding = 'gzip'
        else:
            encoding = None
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        if encoding:
            self.send_header('Content-Encoding', encoding)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/incidents/index.json':
            return self.send_json(json.dumps(list_incidents()).encode())
        local = self.translate_path(path)
        if path.endswith(('.json', '.jsonl')) and os.path.isfile(local) and 'gzip' in self.headers.get('Accept-Encoding', ''):
            mtime = os.path.getmtime(local)
            if _gz.get(local, (None,))[0] != mtime:  # compress big datasets once, not per request
                with open(local, 'rb') as f:
                    _gz[local] = (mtime, gzip.compress(f.read(), 5))
            body = _gz[local][1]
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Encoding', 'gzip')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        return super().do_GET()

    def do_PUT(self):
        m = re.fullmatch(r'/incidents/([\w-]+)\.json', self.path)
        if not m or m.group(1) == 'index':
            return self.send_error(404)
        try:
            data = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
        except ValueError:
            return self.send_error(400, 'invalid JSON')
        if not isinstance(data, dict) or not isinstance(data.get('actions'), list):
            return self.send_error(400, 'not an incident (expected an "actions" list)')
        os.makedirs(INCIDENTS, exist_ok=True)
        path = os.path.join(INCIDENTS, m.group(1) + '.json')
        if os.path.exists(path):  # a page opened before the story was written: keep the story
            try:
                old = json.load(open(path, encoding='utf-8'))
            except ValueError:
                old = {}
            for key in ('story', 'story_style'):
                if key not in data and key in old:
                    data[key] = old[key]
        with open(path + '.tmp', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(path + '.tmp', path)
        record_locked_cells(m.group(1), data)
        self.send_response(204)
        self.end_headers()
        print(f'saved {os.path.relpath(path)} ({len(data["actions"])} actions)')

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')  # refresh always picks up re-converted data
        super().end_headers()

    def log_message(self, fmt, *args):
        pass


def record_locked_cells(name, data):
    """Keep the text of the locked story cells, as saved from the viewer, in incidents/.locked/<name>.json. A person
    locks a cell with its lock button (new cells start locked). check_incidents.py compares the incident file against
    this record, so a locked cell that something else changed, unlocked or removed is caught."""
    cells = data.get('story') if isinstance(data.get('story'), list) else []
    locked = {c['id']: {'title': c.get('title'), 'body': '\n'.join(c['body']) if isinstance(c.get('body'), list) else str(c.get('body') or '')}
              for c in cells if isinstance(c, dict) and c.get('id') and c.get('locked', c.get('author') == 'human')}
    folder = os.path.join(INCIDENTS, '.locked')
    path = os.path.join(folder, name + '.json')
    if not locked and not os.path.exists(path):
        return
    os.makedirs(folder, exist_ok=True)
    with open(path + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(locked, f, ensure_ascii=False, indent=1)
    os.replace(path + '.tmp', path)


def list_incidents():
    out = []
    if not os.path.isdir(INCIDENTS):
        return out
    for fn in sorted(os.listdir(INCIDENTS)):
        if not fn.endswith('.json'):
            continue
        try:
            with open(os.path.join(INCIDENTS, fn), encoding='utf-8') as f:
                d = json.load(f)
        except (ValueError, OSError):
            continue
        out.append({'id': fn[:-5], 'name': d.get('name') or fn[:-5], 'dataset': d.get('dataset'),
                    'from_to': d.get('from_to'), 'tags': d.get('tags') or [], 'actions': d.get('actions') or []})
    return out


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8000)
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--no-open', action='store_true')
    a = ap.parse_args()
    server = http.server.ThreadingHTTPServer((a.host, a.port), functools.partial(Handler, directory=HERE))
    url = f'http://localhost:{a.port}/'
    print(f'Incident viewer at {url}  (incidents save to {os.path.relpath(INCIDENTS)}/; Ctrl+C to stop)')
    if not a.no_open:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

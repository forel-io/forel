"""Serve the viewer for a workspace, and save the incidents a person edits in it.

The page comes from this package; data/ and incidents/ come from the workspace:
  GET /data/...                  the workspace's datasets (JSON is gzipped on the way out: datasets are tens of MB)
  GET /incidents/index.json      a listing of every incident file (built on request)
  GET /incidents/versions.json   {incident id: version} for every incident, so the page notices files changed on disk
  GET /incidents/<id>.json       one incident, with its version in the X-Forel-Version header
  PUT /incidents/<id>.json       save one incident. The page sends the version it last loaded or saved in
                                 X-Forel-Base; if the file has changed since (an agent wrote it), the save is refused
                                 with 409 and the current file, which the page merges with its own edits and saves again
  GET /export/<id>.zip           the incident and its dataset as a zip to share (forel export), at most 60 MB
A version is the file's modification time in nanoseconds.
"""
import functools, gzip, http.server, json, os, re, socket, tempfile, webbrowser

VIEWER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'viewer')
_gz = {}  # path -> (mtime, gzipped bytes)


def version(path):
    try:
        return str(os.stat(path).st_mtime_ns)
    except OSError:
        return ''


class Handler(http.server.SimpleHTTPRequestHandler):
    workspace = '.'

    @property
    def incidents(self):
        return os.path.join(self.workspace, 'incidents')

    def translate_path(self, path):  # /data/ and /incidents/ from the workspace, everything else from the package
        p = path.split('?')[0].split('#')[0]
        for top in ('/data/', '/incidents/'):
            if p.startswith(top):
                rel = os.path.normpath(p[1:]).replace('\\', '/')
                if rel.startswith('..') or '/../' in rel:
                    return os.path.join(VIEWER, '__nope__')
                return os.path.join(self.workspace, rel)
        return super().translate_path(path)

    def send_body(self, code, body, headers=()):
        gz = len(body) > 1024 and 'gzip' in self.headers.get('Accept-Encoding', '')
        if gz:
            body = gzip.compress(body, 5)
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        if gz:
            self.send_header('Content-Encoding', 'gzip')
        for k, v in headers:
            self.send_header(k, v)
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split('?')[0]
        if path == '/incidents/index.json':
            return self.send_body(200, json.dumps(list_incidents(self.incidents)).encode())
        if path == '/incidents/versions.json':
            return self.send_body(200, json.dumps(incident_versions(self.incidents)).encode())
        m = re.fullmatch(r'/incidents/([\w-]+)\.json', path)
        if m:
            f = os.path.join(self.incidents, m.group(1) + '.json')
            if not os.path.isfile(f):
                return self.send_error(404)
            v = version(f)
            with open(f, 'rb') as fh:
                return self.send_body(200, fh.read(), [('X-Forel-Version', v)])
        m = re.fullmatch(r'/export/([\w-]+)\.zip', path)
        if m:
            return self.send_export(m.group(1))
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

    def send_export(self, name):
        from . import export
        fd, tmp = tempfile.mkstemp(suffix='.zip'); os.close(fd)
        try:
            try:
                m = export.export(self.workspace, name, tmp, log=lambda s: print(f'forel export: {s}', flush=True))
            except FileNotFoundError as e:
                return self.send_error(404, str(e))
            except ValueError as e:
                return self.send_error(422, str(e))
            summary = f'{m["events"]:,} of {m["dataset_events"]:,} events' if m['cut'] else f'whole dataset, {m["events"]:,} events'
            self.send_response(200)
            self.send_header('Content-Type', 'application/zip')
            self.send_header('Content-Disposition', f'attachment; filename="{name}.zip"')
            self.send_header('Content-Length', str(m['bytes']))
            self.send_header('X-Forel-Export', summary)
            self.end_headers()
            with open(tmp, 'rb') as f:
                while chunk := f.read(1 << 20):
                    self.wfile.write(chunk)
        finally:
            os.remove(tmp)

    def do_PUT(self):
        m = re.fullmatch(r'/incidents/([\w-]+)\.json', self.path)
        if not m or m.group(1) in ('index', 'versions'):
            return self.send_error(404)
        try:
            data = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))))
        except ValueError:
            return self.send_error(400, 'invalid JSON')
        if not isinstance(data, dict) or not isinstance(data.get('actions'), list):
            return self.send_error(400, 'not an incident (expected an "actions" list)')
        os.makedirs(self.incidents, exist_ok=True)
        path = os.path.join(self.incidents, m.group(1) + '.json')
        base = self.headers.get('X-Forel-Base')
        if base is not None and os.path.exists(path) and version(path) != base:  # changed on disk since the page read it
            with open(path, 'rb') as fh:
                return self.send_body(409, fh.read(), [('X-Forel-Version', version(path))])
        with open(path + '.tmp', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
        os.replace(path + '.tmp', path)
        record_locked_cells(self.incidents, m.group(1), data)
        self.send_body(200, json.dumps({'version': version(path)}).encode(), [('X-Forel-Version', version(path))])

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')  # refresh always picks up re-converted data
        super().end_headers()

    def log_message(self, fmt, *args):
        pass


def record_locked_cells(incidents, name, data):
    """Keep the text of the locked story cells, as saved from the viewer, in incidents/.locked/<name>.json. A person
    locks a cell with its lock button (new cells start locked). `forel check` compares the incident file against
    this record, so a locked cell that something else changed, unlocked or removed is caught."""
    cells = data.get('story') if isinstance(data.get('story'), list) else []
    locked = {c['id']: {'title': c.get('title'), 'body': '\n'.join(c['body']) if isinstance(c.get('body'), list) else str(c.get('body') or '')}
              for c in cells if isinstance(c, dict) and c.get('id') and c.get('locked', c.get('author') == 'human')}
    folder = os.path.join(incidents, '.locked')
    path = os.path.join(folder, name + '.json')
    if not locked and not os.path.exists(path):
        return
    os.makedirs(folder, exist_ok=True)
    with open(path + '.tmp', 'w', encoding='utf-8') as f:
        json.dump(locked, f, ensure_ascii=False, indent=1)
    os.replace(path + '.tmp', path)


def incident_versions(incidents):
    if not os.path.isdir(incidents):
        return {}
    return {fn[:-5]: version(os.path.join(incidents, fn)) for fn in sorted(os.listdir(incidents)) if fn.endswith('.json')}


def list_incidents(incidents):
    out = []
    if not os.path.isdir(incidents):
        return out
    for fn in sorted(os.listdir(incidents)):
        if not fn.endswith('.json'):
            continue
        try:
            with open(os.path.join(incidents, fn), encoding='utf-8') as f:
                d = json.load(f)
        except (ValueError, OSError):
            continue
        out.append({'id': fn[:-5], 'name': d.get('name') or fn[:-5], 'dataset': d.get('dataset'),
                    'from_to': d.get('from_to'), 'tags': d.get('tags') or [], 'actions': d.get('actions') or []})
    return out


def free_port(host, port):
    """port, or the next free one after it."""
    for p in range(port, port + 50):
        with socket.socket() as s:
            try:
                s.bind((host, p))
                return p
            except OSError:
                continue
    raise SystemExit(f'no free port between {port} and {port + 49}')


def serve(workspace, host='127.0.0.1', port=8000, open_browser=False, path=''):
    workspace = os.path.abspath(workspace)
    if not os.path.isfile(os.path.join(workspace, 'data', 'index.json')):
        raise SystemExit(f'{workspace} is not a forel workspace (no data/index.json). Create one with: forel init {workspace}')
    port = free_port(host, port)
    handler = type('WorkspaceHandler', (Handler,), {'workspace': workspace})
    server = http.server.ThreadingHTTPServer((host, port), functools.partial(handler, directory=VIEWER))
    url = f'http://{"localhost" if host in ("127.0.0.1", "0.0.0.0") else host}:{port}/{path}'
    print(f'forel: serving {workspace} at {url}', flush=True)
    print(f'       incidents save to {os.path.join(workspace, "incidents")}/ (Ctrl+C to stop)', flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass

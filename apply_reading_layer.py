"""Inject reading-layer.html into the viewer (forel/viewer/index.html), just before </body>.

    python3 apply_reading_layer.py            # add or refresh the layer
    python3 apply_reading_layer.py --remove   # back to the upstream viewer

Rerunnable: an earlier copy of the layer (between the reading-layer:start / :end comments) is replaced.
Rerun it after editing reading-layer.html or after updating forel from upstream.
"""
import os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
VIEWER = os.path.join(HERE, 'forel', 'viewer', 'index.html')
LAYER = os.path.join(HERE, 'reading-layer.html')
BLOCK = re.compile(r'<!-- reading-layer:start.*?<!-- reading-layer:end -->\n?', re.S)


def main():
    html = BLOCK.sub('', open(VIEWER, encoding='utf-8').read())
    if '--remove' not in sys.argv:
        layer = open(LAYER, encoding='utf-8').read().rstrip('\n') + '\n'
        if html.count('</body>') != 1:
            raise SystemExit('expected exactly one </body> in the viewer')
        html = html.replace('</body>', layer + '</body>')
    with open(VIEWER, 'w', encoding='utf-8') as f:
        f.write(html)
    print('removed the reading layer' if '--remove' in sys.argv else f'reading layer applied to {VIEWER}')


if __name__ == '__main__':
    main()

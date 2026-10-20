"""Export the current mask geometry (make_masks.py) and film images for the 3D viewer page."""
import sys, os, json, base64, io
sys.path.insert(0, os.path.dirname(__file__))
import make_masks as m
from render2 import render
import numpy as np
from PIL import Image
from shapely.geometry import box

def rings(g):
    out = []
    for p in m.polys(g.buffer(0)):
        out.append({'ext': [list(map(lambda v: round(v, 3), c)) for c in p.exterior.coords[:-1]],
                    'holes': [[list(map(lambda v: round(v, 3), c)) for c in h.coords[:-1]] for h in p.interiors]})
    return out

def film_png(fn, ppm=8):
    h = m.FILM / 2
    clear = render(fn, -h, -h, h, h, ppm)
    rgba = np.zeros(clear.shape + (4,), np.uint8)
    rgba[~clear] = (22, 24, 30, 225)        # dark emulsion
    rgba[clear] = (255, 255, 255, 18)       # clear film
    b = io.BytesIO(); Image.fromarray(rgba, 'RGBA').save(b, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()

V = m.VERSION
D = os.path.join(os.path.dirname(__file__), '..', 'Insulation_Mask', V)
insul_left = m.m1_clear()                   # what survives M1 development (inside the insulation edge)
text = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'viewer', 'omnis_text.json')))
sq = lambda w, cx=0.0, cy=0.0, h=None: [[cx - w/2, cy - (h or w)/2], [cx + w/2, cy - (h or w)/2], [cx + w/2, cy + (h or w)/2], [cx - w/2, cy + (h or w)/2]]
ax, ay, aw, ah = m.OPENINGS['active']; px, py, pw, ph = m.OPENINGS['pad']
f = lambda v: '%.2f' % v
dims = ('glass %g × %g<br>insulation edge %g × %g<br>' % (m.GLASS, m.GLASS, m.INSUL, m.INSUL) +
        'active %g × %g, centre (%s, %s)<br>pad %g × %g, centre (%s, %s)<br>' % (aw, ah, f(ax), f(ay), pw, ph, f(px), f(py)) +
        'top margin %g, side margin %g, pad–active gap %g<br>' % (m.TOP_MARGIN, m.SIDE_MARGIN, m.PAD_GAP) +
        'pillars %d × Ø%g, hex pitch %g<br>M2 wall from %.2f outside active and pad edges to a rectangle %.2f outside both<br>'
        % (len(m.pillars()), m.PILLAR_D, m.PILLAR_P, m.M2_IN, m.M2_OUT) +
        'mesh cut: rectangle %.3f outside active and pad' % ((m.M2_IN + m.M2_OUT) / 2))
h = m.FILM / 2
data = {
    'title': 'OMNIS Bulk Stack', 'heading': 'OMNIS bulk stack, masks %s' % V, 'sub': text['sub'],
    'substrate': 'glass', 'sub_thick': 1.1, 'center': [0, 0], 'span': m.GLASS,
    'board': sq(m.GLASS), 'sheet': sq(m.INSUL), 'film': [-h, -h, h, h], 'mesh_full': [-56, -56, 56, 56],
    'm1': rings(insul_left), 'm2': rings(m.m2_clear()),
    'pillars': [{'d': m.PILLAR_D, 'pts': [[round(x, 3), round(y, 3)] for x, y in m.pillars()]}],
    'active': sq(aw, ax, ay, ah), 'pads': [sq(pw, px, py, ph)],
    'cut': [[round(x, 3), round(y, 3)] for x, y in m.mesh_cut().coords[:-1]],
    'film_m1': film_png(os.path.join(D, 'OMNIS-Mask_M1_%s.gbr' % V)),
    'film_m2': film_png(os.path.join(D, 'OMNIS-Mask_M2_%s.gbr' % V)),
    'steps': text['steps'], 'legend': text['legend'], 'note': text['note'], 'dims': dims,
}
out = sys.argv[1]
open(out, 'w').write(json.dumps(data))
print('wrote', out, os.path.getsize(out) // 1024, 'kB')

"""Export the P2 basket films (KiCad Gerbers, P2_BASKET-Mask_M1/M2_V1) as geometry for the 3D stack viewer.

Film layout read from the files: sections 0 and 1 are dark (LPD), M2 section 2 is clear (LPC) and holds the pillars,
each drawn as two half-circle arcs (width 0.4 mm, radius 0.2 -> disc 0.8 mm; width 3.075 -> 6.15 mm support pillars).
The hole in section 1 is the insulation edge. Units mm, KiCad coordinates.
"""
import sys, os, json, base64, io
sys.path.insert(0, os.path.dirname(__file__))
from gerber_parse import parse
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union

P2 = os.environ.get('P2_DIR', '/local/home/ak271430/Documents/PostDocSaclay/Detector_Drawings/Version_Apr26/Insulation_masks/V1')
F1, F2 = (os.path.join(P2, 'P2_BASKET-Mask_%s_V1.gbr' % n) for n in ('M1', 'M2'))
FILM = (-6.6, -35.1, 693.7, 565.2)
PILLAR_W = {0.4: 'pillar', 3.075: 'support'}
GAP_THICK = 0.15

def geo(sec):
    g = [Polygon(r).buffer(0) for r in sec['regions'] if len(r) > 2]
    g += [(LineString(p) if len(p) > 1 else Point(p[0])).buffer(w / 2, 8) for w, p in sec['strokes']]
    return unary_union(g)

def polys(g):
    return [] if g.is_empty else [p for p in getattr(g, 'geoms', [g]) if p.geom_type == 'Polygon']

def rings(g, tol=0.02):
    out = []
    for p in polys(g.buffer(0)):
        p = p.simplify(tol)
        if p.is_empty or p.area < 0.05: continue
        r = lambda c: [[round(x, 3), round(y, 3)] for x, y in c.coords[:-1]]
        out.append({'ext': r(p.exterior), 'holes': [r(h) for h in p.interiors]})
    return out

def pillars(sec):
    """centres of the arc pairs, grouped by stroke width"""
    out = {}
    for w, p in sec['strokes']:
        if w not in PILLAR_W: continue
        (x0, y0), (x1, y1) = p[0], p[-1]
        out.setdefault(w, set()).add((round((x0 + x1) / 2, 3), round((y0 + y1) / 2, 3)))
    return {w: sorted(v) for w, v in out.items()}

def film_png(secs, ppm=2.0):
    x0, y0, x1, y1 = FILM
    W, H = int(round((x1 - x0) * ppm)), int(round((y1 - y0) * ppm))
    img = Image.new('L', (W, H), 0); dr = ImageDraw.Draw(img)
    T = lambda q: ((q[0] - x0) * ppm, (y1 - q[1]) * ppm)
    for s in secs:
        c = 255 if s['pol'] == 'D' else 0
        for r in s['regions']:
            if len(r) > 2: dr.polygon([T(q) for q in r], fill=c)
        for w, pts in s['strokes']:
            lw = max(1, int(round(w * ppm))); Q = [T(q) for q in pts]
            if len(Q) > 1: dr.line(Q, fill=c, width=lw, joint='curve')
            for q in (Q[0], Q[-1]): dr.ellipse([q[0] - lw / 2, q[1] - lw / 2, q[0] + lw / 2, q[1] + lw / 2], fill=c)
    clear = np.array(img) == 0
    rgba = np.zeros(clear.shape + (4,), np.uint8)
    rgba[~clear] = (22, 24, 30, 225); rgba[clear] = (255, 255, 255, 18)
    b = io.BytesIO(); Image.fromarray(rgba, 'RGBA').save(b, 'PNG', optimize=True)
    return 'data:image/png;base64,' + base64.b64encode(b.getvalue()).decode()

s1, s2 = parse(F1), parse(F2)
film = box(*FILM)
outline = geo(s1[1])
edge = max((Polygon(h) for p in polys(outline) for h in p.interiors), key=lambda p: p.area)   # insulation edge
m1 = film.difference(unary_union([geo(s1[0]), outline])).intersection(edge)
m2 = film.difference(unary_union([geo(s2[0]), geo(s2[1])])).intersection(edge)
# M1: the thin line on the active edge is the clear piece with exactly one hole, around the active zone
sliver = max((p for p in polys(m1) if len(p.interiors) == 1), key=lambda p: p.area)
active = Polygon(sliver.interiors[0])
# M2: the rim wall is the clear piece that encloses the active zone; the pad is its small square hole
rim = next(p for p in polys(m2) if Polygon(p.exterior).contains(active.representative_point()) and p.area < edge.area / 4)
pads = [Polygon(h) for h in rim.interiors if 20 < Polygon(h).area < 100]   # the 7 x 7 window (not the small corner notch)
outer = max(polys(m2), key=lambda p: p.area)                     # outer Dynamask band on the insulation edge
cut = Polygon(rim.exterior).buffer(-1.32, join_style=2)
cut_alt = edge.buffer(-5.0, join_style=2)                       # middle of the ~10 mm edge band
pl = pillars(s2[2])
c = edge.centroid
xs, ys = edge.exterior.xy
span = max(max(xs) - min(xs), max(ys) - min(ys))
lst = lambda g: [[round(x, 3), round(y, 3)] for x, y in g.exterior.coords[:-1]]

steps = [
  {'t': 'Assembled detector with both films',
   'd': 'Finished P2 basket with the two films lifted above it. <b>M1</b> (insulation) leaves the green frame between the active zone and the board edge, with the holes left dark, plus a thin line on the active edge. <b>M2</b> (Dynamask) leaves the blue rim wall around the active zone, a wider band on top of the insulation along the board edge, and %d pillars (Ø0.8 mm, 4 mm pitch) plus %d support pillars (Ø6 mm). The rim wall overlaps the insulation by about 0.25 mm on each side.' % (len(pl.get(0.4, [])), len(pl.get(3.075, []))),
   'show': ['glass', 'insFrame', 'wall', 'pillars', 'meshCut', 'filmM1', 'filmM2', 'marks']},
  {'t': 'Clean board',
   'd': 'Bare readout board. The dashed outline is the active zone (the inside edge of the M1 line); the orange square is the 7 × 7 mesh contact window in the bottom-right corner. The outline shown is the insulation edge drawn on the films; the films carry no separate board outline.',
   'show': ['glass', 'marks']},
  {'t': 'Laminate the insulation film',
   'd': 'The insulation photoresist covers the board up to the insulation edge. It is unexposed, so it would all wash off if developed now.',
   'show': ['glass', 'insSheet', 'marks']},
  {'t': 'Expose through M1',
   'd': 'M1 is aligned with the crosses and exposed. Clear on M1: the outer frame (the holes stay dark) and the 0.56 mm line on the active edge. The active zone and the 2.1 mm band left for the rim wall stay dark.',
   'show': ['glass', 'insSheet', 'filmM1', 'uv', 'marks']},
  {'t': 'Develop the insulation',
   'd': 'The unexposed film dissolves. The frame and the edge line stay; the active zone and the band between them are bare, waiting for the Dynamask rim wall.',
   'show': ['glass', 'insFrame', 'marks']},
  {'t': 'Laminate Dynamask and the mesh',
   'd': 'Dynamask is laminated, the mesh laid on it and covered by the top Dynamask layer. The layers under the mesh set the 150 µm gap.',
   'show': ['glass', 'insFrame', 'dynaSheet', 'meshFull', 'marks']},
  {'t': 'Expose through M2',
   'd': 'M2 is aligned with the same crosses and exposed. Clear on M2: the 2.64 mm rim wall, which overlaps the insulation by about 0.25 mm on both sides so there is no unexposed seam, the band along the board edge (on top of the insulation), the pillars, and a ring around the 7 × 7 contact window, merged with the rim.',
   'show': ['glass', 'insFrame', 'dynaSheet', 'meshFull', 'filmM2', 'uv', 'marks']},
  {'t': 'Develop the Dynamask',
   'd': 'The developer removes the unexposed Dynamask through the mesh. The mesh is left on the pillars, held by the rim wall around the active zone, and by the band along the board edge. In the contact window the mesh is bare. Between the rim and the edge band it lies on the insulation.',
   'show': ['glass', 'insFrame', 'wall', 'pillars', 'meshFull', 'marks']},
  {'t': 'Cut the mesh',
   'd': 'Solid red: a cut along the middle of the rim wall, the reading used for the OMNIS masks. Dashed red: the other possibility, a cut on the edge band, which keeps the mesh over the insulation frame. The films do not say which one the workshop uses.',
   'show': ['glass', 'insFrame', 'wall', 'pillars', 'meshCut', 'marks']},
]
ax0, ay0, ax1, ay1 = active.bounds
dims = ('insulation edge %.1f × %.1f (bounding box)<br>active zone %.1f × %.1f (bounding box), %.0f cm²<br>' % (
            edge.bounds[2] - edge.bounds[0], edge.bounds[3] - edge.bounds[1], ax1 - ax0, ay1 - ay0, active.area / 100) +
        'contact window %s<br>' % ', '.join('%.1f × %.1f at (%.1f, %.1f)' % (p.bounds[2] - p.bounds[0], p.bounds[3] - p.bounds[1], p.centroid.x, p.centroid.y) for p in pads) +
        'pillars %d × Ø0.8, pitch 4; support pillars %d × Ø6.15<br>' % (len(pl.get(0.4, [])), len(pl.get(3.075, []))) +
        'M1 line 0.56 on the active edge, then 2.1 dark band<br>M2 rim wall 2.64, overlaps M1 ~0.25 on each side<br>coordinates: KiCad, mm')
data = {
    'title': 'P2 Bulk Stack', 'heading': 'P2 basket bulk stack, masks V1',
    'sub': 'readout board · two-film bulk (M1 insulation, M2 Dynamask) · geometry read from P2_BASKET-Mask_M1/M2_V1.gbr',
    'substrate': 'pcb', 'sub_thick': 1.6, 'center': [round(c.x, 2), round(c.y, 2)], 'span': round(span, 2),
    'board': lst(edge), 'sheet': lst(edge), 'film': list(FILM),
    'mesh_full': [edge.bounds[0] - 8, edge.bounds[1] - 8, edge.bounds[2] + 8, edge.bounds[3] + 8],
    'm1': rings(m1), 'm2': rings(m2),
    'pillars': [{'d': 0.8, 'pts': [list(q) for q in pl.get(0.4, [])]}, {'d': 6.15, 'pts': [list(q) for q in pl.get(3.075, [])]}],
    'active': lst(active.simplify(0.02)), 'pads': [lst(p) for p in pads],
    'cut': lst(cut.simplify(0.02)), 'cut_alt': lst(cut_alt.simplify(0.02)),
    'film_m1': film_png(s1), 'film_m2': film_png(s2),
    'steps': steps, 'dims': dims,
    'legend': [['--insul', 'Insulation film, kept where M1 is clear'],
               ['--dyna', 'Dynamask rim wall, edge band and pillars, kept where M2 is clear'],
               ['--mesh', 'Mesh (red: cut along the rim wall; dashed: cut on the edge band)'],
               ['--pad', 'Mesh contact window (7 × 7)'], ['--accent', 'UV exposure']],
    'note': 'Geometry is read from the P2 V1 films. Thicknesses are illustrative and drawn exaggerated; only the 150 µm gap is from the P2 bulk order (CERN quote 3717-A). The step order and the mesh cut are assumptions to check with the CERN workshop.',
}
out = sys.argv[1]
open(out, 'w').write(json.dumps(data, separators=(',', ':')))
print('wrote', out, os.path.getsize(out) // 1024, 'kB | pillars', {w: len(v) for w, v in pl.items()},
      '| active %.1f x %.1f' % (ax1 - ax0, ay1 - ay0), '| pads', len(pads), '| m1/m2 pieces', len(data['m1']), len(data['m2']))

"""Two-mask (M1/M2) bulk insulation films for the OMNIS optical micromegas, 9.5x9.5 cm glass.

Same overlap scheme as P2_BASKET-Mask_M1/M2_V1. Negative-tone resist: CLEAR = exposed = stays.
The active zone and the mesh contact pad are each surrounded by, with d = distance outward from the opening edge:
  M1 clear : 0 .. SLIVER            (thin line that defines the opening edge)
  M1 dark  : SLIVER .. M1_FRAME     (gap left for M2)
  M1 clear : M1_FRAME .. INSUL edge (outer insulation frame, = mesh cut, 1 mm inside the glass)
  M2 clear : M2_IN .. M2_OUT        (rim band, overlaps M1 by 0.25 mm on both sides)
  M2 clear : pillars inside the active zone only
The outer edge of the M2 wall (and the inner edge of the M1 frame) is the rectangle enclosing both openings,
so the wall fills the corner beside the pad and the mesh is held all the way to the contact window.
The mesh is cut once, as a plain rectangle along the middle of the outer wall (mesh_cut(), a process guide,
not drawn on the films): straight cuts only, no pocket to cut around the pad.
(V3 = 5 mm M2 wall with a 2 mm outer-only overlap was tried and dropped in favour of the proven P2 scheme.)
Units mm, origin = glass centre.
"""
import math, os, sys, datetime
from shapely.geometry import box, Polygon
from shapely.ops import unary_union
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties

VERSION = 'V2'
GLASS = 95.0                        # glass outline
INSUL = GLASS - 2*1.0               # insulation (and mesh) stops 1 mm inside the glass edge
TOP_MARGIN = 10.0                   # glass edge -> active zone, top
SIDE_MARGIN = 11.0                  # glass edge -> active zone, left and right
PAD_W, PAD_H = 15.0, 7.0            # contact pad, long side horizontal
PAD_CY = -GLASS/2 + 13.0            # pad centre 13 mm above the glass bottom edge
PAD_GAP = 5.0                       # pad -> active zone (< 2*M2_OUT, so the walls merge)
# rectangular active zone: width set by the side margins, height by the top margin, pad and gap; centred left-right
ACT_W = GLASS - 2*SIDE_MARGIN
ACT_H = GLASS - TOP_MARGIN - PAD_GAP - (PAD_CY + PAD_H/2 + GLASS/2)
ACT_CY = GLASS/2 - TOP_MARGIN - ACT_H/2
PAD_CX = 24.25                      # bottom right, kept where it was with the 63.5 mm square active zone (x 16.75 .. 31.75)
PILLAR_D, PILLAR_P = 0.5, 6.0       # hexagonal grid (P = nearest-neighbour distance), centred in the active zone

# P2 V1 values (measured on the P2 films), rounded
SLIVER = 0.55
M1_FRAME = 2.70
M2_IN, M2_OUT = 0.30, 2.95          # -> overlaps of 0.25 mm on each side, M1 sliver protrudes 0.30 mm

FILM = 130.0                        # film field (dark), fiducials and labels outside the glass
FID = 57.5                          # fiducial cross centres (+-FID, +-FID)

def rect(cx, cy, w, h, d=0.0):
    """rectangle grown by d with square corners (mitre offset)"""
    return box(cx - w/2 - d, cy - h/2 - d, cx + w/2 + d, cy + h/2 + d)

OPENINGS = {'active': (0.0, ACT_CY, ACT_W, ACT_H), 'pad': (PAD_CX, PAD_CY, PAD_W, PAD_H)}
WALLED = ('active', 'pad')          # openings with the M1/M2 mesh wall; the others are plain M1 openings
glass = rect(0, 0, GLASS, GLASS)
insul = rect(0, 0, INSUL, INSUL)
grown = lambda d: unary_union([rect(*OPENINGS[k], d) for k in WALLED])
envelope = lambda d: box(*grown(d).bounds)   # rectangle enclosing all walled openings grown by d
plain = unary_union([rect(*o) for k, o in OPENINGS.items() if k not in WALLED])

def pillars():
    """hexagonal grid, PILLAR_P between nearest neighbours, centred in the active zone;
    rows alternate n and n-1 pillars so the pattern stays symmetric; outer pillars at least half a pitch from the edges"""
    dy = PILLAR_P * math.sqrt(3) / 2
    rows = int((ACT_H - PILLAR_P) // dy) + 1
    n = int((ACT_W - PILLAR_P) // PILLAR_P) + 1
    out = []
    for j in range(rows):
        y = ACT_CY + (j - (rows - 1) / 2) * dy
        k = n if j % 2 == 0 else n - 1
        out += [((i - (k - 1) / 2) * PILLAR_P, y) for i in range(k)]
    return out

def fiducials():
    arm, w = 3.0, 0.3
    out = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * FID, sy * FID
            out.append(unary_union([rect(x, y, 2*arm, w), rect(x, y, w, 2*arm)]))
    return unary_union(out)

def label(text, x, y, size=2.2):
    tp = TextPath((0, 0), text, size=size, prop=FontProperties(family='DejaVu Sans Mono'))
    polys = [Polygon(p) for p in tp.to_polygons() if len(p) > 2]
    # even-odd: letters with counters (o, 0, 8 ...) come as outer + inner contours
    geo = None
    for p in sorted(polys, key=lambda p: -p.area):
        p = p.buffer(0)
        geo = p if geo is None else (geo.difference(p) if geo.contains(p) else geo.union(p))
    from shapely.affinity import translate
    return translate(geo, x, y)

def m1_clear():
    frame = insul.difference(envelope(M1_FRAME)).difference(plain)
    slivers = unary_union([rect(*OPENINGS[k], SLIVER).difference(rect(*OPENINGS[k])) for k in WALLED])
    return unary_union([frame, slivers])

def m2_clear():
    return envelope(M2_OUT).difference(grown(M2_IN))

def mesh_cut():
    """single rectangular mesh cut along the middle of the outer M2 wall, enclosing the active zone and the pad"""
    return envelope((M2_IN + M2_OUT) / 2).exterior

def polys(g):
    if g.is_empty: return []
    return list(getattr(g, 'geoms', [g]))

def fmt(v): return '%d' % round(v * 1e6)

def region(ring):
    pts = list(ring.coords)
    s = ['G36*', 'X%sY%sD02*' % (fmt(pts[0][0]), fmt(pts[0][1]))]
    s += ['X%sY%sD01*' % (fmt(x), fmt(y)) for x, y in pts[1:]]
    return s + ['G37*']

def write(fn, name, clear, with_pillars):
    stamp = datetime.datetime.now().isoformat(timespec='seconds')
    L = ['%TF.GenerationSoftware,optical_micromegas/tools/make_masks.py*%',
         '%%TF.CreationDate,%s*%%' % stamp,
         '%TF.FileFunction,Other,Insulation film*%',
         '%FSLAX46Y46*%', '%MOMM*%',
         'G04 %s : CLEAR = exposed. Origin = glass centre. Glass %gx%g mm, insulation %gx%g mm*' % (name, GLASS, GLASS, INSUL, INSUL),
         '%ADD10C,{:.6f}*%'.format(PILLAR_D),
         '%LPD*%', 'G01*']
    L += region(rect(0, 0, FILM, FILM).exterior)              # dark film field
    extra = [fiducials(), label('OMNIS 9.5x9.5  %s_%s' % (name, VERSION), -50, -FILM/2 + 2.5)]
    if with_pillars:
        extra.append(label('pillars D%.3fmm hex P%gmm' % (PILLAR_D, PILLAR_P), 10, -FILM/2 + 2.5))
    geo = unary_union([clear] + extra)
    # largest first, so anything sitting inside a hole is emitted after the hole
    for p in sorted(polys(geo), key=lambda p: -p.area):
        L.append('%LPC*%'); L += region(p.exterior)
        for h in p.interiors:
            L.append('%LPD*%'); L += region(h)
    if with_pillars:
        L += ['%LPC*%', 'D10*'] + ['X%sY%sD03*' % (fmt(x), fmt(y)) for x, y in pillars()]
    L.append('M02*')
    open(fn, 'w').write('\n'.join(L) + '\n')

if __name__ == '__main__':
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..', 'Insulation_Mask', VERSION)
    os.makedirs(out, exist_ok=True)
    write(os.path.join(out, 'OMNIS-Mask_M1_%s.gbr' % VERSION), 'Mask_M1', m1_clear(), False)
    write(os.path.join(out, 'OMNIS-Mask_M2_%s.gbr' % VERSION), 'Mask_M2', m2_clear(), True)
    print('written to', os.path.abspath(out), '| pillars:', len(pillars()))

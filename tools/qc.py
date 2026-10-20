"""QC of the OMNIS insulation films: edge profiles, double/non-exposed areas, overview and close-up figures."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from render2 import render, runs
import make_masks as m
import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from scipy import ndimage
V = m.VERSION
D = os.path.join(os.path.dirname(__file__), '..', 'Insulation_Mask', V) + '/'
M1 = D + 'OMNIS-Mask_M1_%s.gbr' % V; M2 = D + 'OMNIS-Mask_M2_%s.gbr' % V
os.makedirs(D + 'QC', exist_ok=True)
G, I = m.GLASS/2, m.INSUL/2
ay0, ay1 = m.ACT_CY - m.ACT_H/2, m.ACT_CY + m.ACT_H/2; ax1 = m.ACT_W/2
px0, px1 = m.PAD_CX - m.PAD_W/2, m.PAD_CX + m.PAD_W/2; py0, py1 = m.PAD_CY - m.PAD_H/2, m.PAD_CY + m.PAD_H/2
ppm = 200; e = 0.005
for name, b, ax in [('vertical cut x=%.2f (glass bottom -> pad -> active)' % m.PAD_CX, (m.PAD_CX-e, -G-1, m.PAD_CX+e, ay0+3), 'y'),
                    ('vertical cut x=-20 (glass bottom -> active)', (-20-e, -G-1, -20+e, ay0+3), 'y'),
                    ('vertical cut x=0 (active -> glass top)', (-e, ay1-3, e, G+1), 'y'),
                    ('horizontal cut y=%.2f (active -> glass right)' % m.ACT_CY, (ax1-3, m.ACT_CY-e, G+1, m.ACT_CY+e), 'x'),
                    ('horizontal cut y=%.2f (pad -> glass right)' % m.PAD_CY, (px1-3, m.PAD_CY-e, G+1, m.PAD_CY+e), 'x')]:
    print('###', name)
    for n, f in (('M1', M1), ('M2', M2)):
        a = render(f, *b, ppm)
        if ax == 'y': v = a[::-1, a.shape[1]//2]; c = b[1] + (np.arange(len(v)) + .5)/ppm
        else: v = a[a.shape[0]//2]; c = b[0] + (np.arange(len(v)) + .5)/ppm
        print(' ', n, '  '.join('%s %.2f..%.2f' % r for r in runs(v, c)))
ppm = 40; b = (-G, -G, G, G)
a1 = render(M1, *b, ppm); a2 = render(M2, *b, ppm)
X, Y = np.meshgrid(b[0] + (np.arange(a1.shape[1]) + .5)/ppm, b[3] - (np.arange(a1.shape[0]) + .5)/ppm)
act = (abs(X) <= ax1 + .03) & (Y >= ay0 - .03) & (Y <= ay1 + .03)
pad = (X >= px0 - .03) & (X <= px1 + .03) & (Y >= py0 - .03) & (Y <= py1 + .03)
ins = (abs(X) < I - .03) & (abs(Y) < I - .03)
ins_out = (abs(X) < I + .03) & (abs(Y) < I + .03)
print('double-exposed area %.1f mm2' % ((a1 & a2).sum()/ppm**2))
print('unexposed inside insulation, outside openings %.2f mm2' % ((~(a1 | a2) & ins & ~act & ~pad).sum()/ppm**2))
print('exposed outside insulation %.2f mm2' % (((a1 | a2) & ~ins_out & (abs(X) < G-.05) & (abs(Y) < G-.05)).sum()/ppm**2))
core = (abs(X) <= ax1 - .5) & (Y >= ay0 + .5) & (Y <= ay1 - .5)
print('pillars in M2 inside active:', ndimage.label(a2 & core)[1])
B = (-65, 65, -65, 65); ppm = 8
a1 = render(M1, B[0], B[2], B[1], B[3], ppm); a2 = render(M2, B[0], B[2], B[1], B[3], ppm)
fig, axs = plt.subplots(1, 3, figsize=(21, 7.4))
for k, (t, a) in enumerate([('M1', a1), ('M2', a2)]):
    axs[k].imshow(a, cmap='gray', extent=B); axs[k].set_title('OMNIS-%s_%s (white = clear, black = dark)' % (t, V))
rgb = np.zeros(a1.shape + (3,)); rgb[..., 0] = a1; rgb[..., 2] = a2; rgb[..., 1] = a1 & a2
axs[2].imshow(rgb, extent=B); axs[2].set_title('overlay: red=M1 clear, blue=M2 clear, white=both')
for a in axs:
    a.plot([-G, G, G, -G, -G], [-G, -G, G, G, -G], 'y--', lw=.8); a.set_xlabel('x [mm]')
plt.tight_layout(); plt.savefig(D + 'QC/OMNIS-Masks_%s_overview.png' % V, dpi=90)
boxes = [(px0-8, -G-1, px1+10, ay0+4, 'pad + gap + active bottom'), (ax1-6, ay1-6, G+1, G+1, 'active top-right corner'),
         (-ax1-6, ay0-6, -ax1+6, ay0+6, 'active bottom-left corner'), (px1-4, -G-1, G+1, py1+3, 'pad bottom-right corner')]
fig, axs = plt.subplots(1, 4, figsize=(24, 6.5)); ppm = 60
for k, (x0, y0, x1, y1, t) in enumerate(boxes):
    a1 = render(M1, x0, y0, x1, y1, ppm); a2 = render(M2, x0, y0, x1, y1, ppm)
    rgb = np.zeros(a1.shape + (3,)); rgb[..., 0] = a1; rgb[..., 2] = a2; rgb[..., 1] = a1 & a2
    axs[k].imshow(rgb, extent=(x0, x1, y0, y1)); axs[k].set_title(t + '\nred=M1, blue=M2, white=both, black=neither'); axs[k].grid(alpha=.3)
    axs[k].plot([-G, G, G, -G, -G], [-G, -G, G, G, -G], 'y--', lw=1)
    axs[k].set_xlim(x0, x1); axs[k].set_ylim(y0, y1)
plt.tight_layout(); plt.savefig(D + 'QC/OMNIS-Masks_%s_boundaries.png' % V, dpi=70)

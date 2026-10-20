import re
from PIL import Image, ImageDraw
import numpy as np
def render(fn,x0,y0,x1,y1,ppm):
    W=int(round((x1-x0)*ppm)); H=int(round((y1-y0)*ppm))
    img=Image.new('L',(W,H),0); dr=ImageDraw.Draw(img)
    T=lambda x,y:((x-x0)*ppm,(y1-y)*ppm)
    pol=255; ap={}; d=None; reg=None
    for line in open(fn):
        line=line.strip()
        if line.startswith('%LP'): pol=255 if line[3]=='D' else 0; continue
        m=re.match(r'%ADD(\d+)C,([\d.]+)',line)
        if m: ap[int(m[1])]=float(m[2]); continue
        m=re.match(r'^D(\d+)\*$',line)
        if m: d=ap[int(m[1])]; continue
        if line=='G36*': reg=[]; continue
        if line=='G37*': dr.polygon(reg,fill=pol); reg=None; continue
        m=re.match(r'X(-?\d+)Y(-?\d+)D0([123])',line)
        if not m: continue
        x,y=int(m[1])/1e6,int(m[2])/1e6
        if reg is not None: reg.append(T(x,y))
        elif m[3]=='3':
            cx,cy=T(x,y); r=d/2*ppm; dr.ellipse([cx-r,cy-r,cx+r,cy+r],fill=pol)
    return ~(np.array(img)>0)   # True = CLEAR
def runs(v,c):
    out=[];s=0
    for i in range(1,len(v)+1):
        if i==len(v) or v[i]!=v[s]: out.append(('CLEAR' if v[s] else 'dark ',c[s],c[i-1])); s=i
    return out

"""Minimal Gerber parser for the KiCad P2 films: per section (one per %TF.GenerationSoftware header) polarity, regions, strokes (arcs flattened) and flashes. Units mm."""
import re, sys, math
from shapely.geometry import Polygon, LineString, Point
from shapely.ops import unary_union
def arcpts(x0,y0,x1,y1,i,j,cw,n=24):
    cx,cy=x0+i,y0+j; r=math.hypot(i,j)
    a0=math.atan2(y0-cy,x0-cx); a1=math.atan2(y1-cy,x1-cx)
    if cw:
        if a1>=a0: a1-=2*math.pi
    else:
        if a1<=a0: a1+=2*math.pi
    if abs(x0-x1)<1e-9 and abs(y0-y1)<1e-9: a1=a0+(-2*math.pi if cw else 2*math.pi)
    return [(cx+r*math.cos(a0+(a1-a0)*k/n), cy+r*math.sin(a0+(a1-a0)*k/n)) for k in range(1,n+1)]
def parse(fn):
    """returns list of sections; each: dict(pol, regions[list of point lists], strokes[(width,pts)], flashes)"""
    secs=[]; cur=None
    ap={}; d=None; x=y=0; mode='G01'; inreg=False; reg=[]; path=None
    for line in open(fn):
        line=line.strip()
        if line.startswith('%TF.GenerationSoftware'):
            cur=dict(pol='D',regions=[],strokes=[],flashes=[]); secs.append(cur); ap={}
        if line.startswith('%LP'): cur['pol']=line[3]
        m=re.match(r'%ADD(\d+)C,([\d.]+)',line)
        if m: ap[int(m[1])]=float(m[2]); continue
        m=re.match(r'^D(\d+)\*$',line)
        if m and int(m[1])>=10: d=ap[int(m[1])]; continue
        if line.startswith('G36'): inreg=True; reg=[]; continue
        if line.startswith('G37'):
            if reg: cur['regions'].append(reg)
            inreg=False; continue
        for g in ('G01','G02','G03'):
            if g in line: mode=g
        m=re.search(r'X(-?\d+)Y(-?\d+)(?:I(-?\d+)J(-?\d+))?D0([123])',line)
        if not m: continue
        nx,ny=int(m[1])/1e6,int(m[2])/1e6; op=m[5]
        if op=='2':
            if inreg:
                if reg: cur['regions'].append(reg)
                reg=[(nx,ny)]
            else:
                path=[(nx,ny)]; cur['strokes'].append((d,path))
        elif op=='1':
            pts=[(nx,ny)] if mode=='G01' else arcpts(x,y,nx,ny,int(m[3])/1e6,int(m[4])/1e6,mode=='G02')
            (reg if inreg else path).extend(pts)
        else: cur['flashes'].append((d,nx,ny))
        x,y=nx,ny
    return secs

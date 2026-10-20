"""Build the 3D stack viewers from viewer/stack_template.html:
viewer/OMNIS_<V>_3D.html (geometry from make_masks.py) and viewer/P2_V1_3D.html (geometry read from the P2 V1 Gerbers)."""
import os, subprocess, sys, json
here = os.path.dirname(os.path.abspath(__file__)); root = os.path.join(here, '..')
sys.path.insert(0, here)
import make_masks as m
template = open(os.path.join(root, 'viewer', 'stack_template.html')).read()
for exporter, name in [('export_viewer_data.py', 'OMNIS_%s' % m.VERSION), ('export_p2_viewer_data.py', 'P2_V1')]:
    data = os.path.join(root, 'viewer', '%s_geometry.json' % name.lower())
    subprocess.run([sys.executable, os.path.join(here, exporter), data], check=True)
    d = open(data).read()
    html = template.replace('__TITLE__', json.loads(d)['title']).replace('__DATA__', d)
    out = os.path.join(root, 'viewer', '%s_3D.html' % name)
    open(out, 'w').write(html)
    print('wrote', os.path.abspath(out), os.path.getsize(out) // 1024, 'kB')

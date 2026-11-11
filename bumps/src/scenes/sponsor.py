"""sponsor: a word from our sponsor. There isn't one. An empty pedestal, beautifully lit."""
import bpy, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

s = reset()
world((0.0, 0.0, 0.0))

# glossy stage floor
plane('floor', 60, (0, 0, 0), mat('floor', (0.012, 0.01, 0.012), 0.12, coat=0.6))

# velvet curtain: a plane with folds
bpy.ops.mesh.primitive_grid_add(x_subdivisions=260, y_subdivisions=4, size=1, location=(0, 5.5, 4), rotation=(math.radians(90), 0, 0))
cur = bpy.context.object; cur.scale = (26, 9, 1)
rng = random.Random(2)
ph = [rng.uniform(0, 6.28) for _ in range(4)]
for v in cur.data.vertices:
    x = v.co.x * 26
    v.co.z += (0.20 * math.sin(x * 4.4 + ph[0]) + 0.10 * math.sin(x * 9.3 + ph[1]) + 0.05 * math.sin(x * 17.0 + ph[2])) * -1
for p in cur.data.polygons: p.use_smooth = True
vel = mat('velvet', (0.33, 0.012, 0.03), 0.75)
try:
    bsdf(vel).inputs['Sheen Weight'].default_value = 1.0
    bsdf(vel).inputs['Sheen Roughness'].default_value = 0.4
    bsdf(vel).inputs['Sheen Tint'].default_value = (1.0, 0.35, 0.4, 1)
except Exception as e: print(e)
cur.data.materials.append(vel)

# pedestal + turntable
white = mat('ped', (0.82, 0.8, 0.76), 0.3, coat=0.4)
cyl('ped', 0.95, 1.5, (0, 0, 0.75), white, verts=96, bevel=0.03)
cyl('foot', 1.1, 0.12, (0, 0, 0.06), white, verts=96, bevel=0.02)
gold = mat('gold', (0.95, 0.68, 0.22), 0.22, metal=1.0)
T = empty('turn', (0, 0, 1.5))
cyl('disc', 0.88, 0.07, (0, 0, 0.035), mat('disc', (0.06, 0.055, 0.07), 0.18, coat=0.8), verts=96, bevel=0.012, parent=T)
cyl('rim', 0.9, 0.035, (0, 0, 0.012), gold, verts=96, parent=T)
for k in range(16):
    a = 2 * math.pi * k / 16
    sphere('stud', 0.022, (0.8 * math.cos(a), 0.8 * math.sin(a), 0.075), gold, segs=12, rings=6, parent=T)
T.rotation_euler = (0, 0, 0); T.keyframe_insert('rotation_euler', frame=1)
T.rotation_euler = (0, 0, 2 * math.pi); T.keyframe_insert('rotation_euler', frame=FRAMES + 1)

# sparkles on the product that is not there: two crossed slivers, facing the camera
star_m = mat('star', (1, 1, 1), emit=(1.0, 0.95, 0.8), emit_strength=30)
def star(loc, f0, size=0.34):
    e = empty('star', loc)
    for rz in (0, 90):
        b = box('ray', (size, 0.004, size * 0.05), (0, 0, 0), star_m, parent=e)
        b.rotation_euler = (0, math.radians(rz), 0)
        b2 = box('ray2', (size * 0.45, 0.004, size * 0.03), (0, 0, 0), star_m, parent=e)
        b2.rotation_euler = (0, math.radians(rz + 45), 0)
    for f, sc in ((f0 - 1, 0.0), (f0 + 3, 1.0), (f0 + 7, 0.55), (f0 + 16, 0.0)):
        e.scale = (sc, sc, sc); e.keyframe_insert('scale', frame=f)
    e.scale = (0, 0, 0); e.keyframe_insert('scale', frame=1)
    e.rotation_euler = (0, 0.0, 0); e.keyframe_insert('rotation_euler', frame=f0 - 1)
    e.rotation_euler = (0, 0.9, 0); e.keyframe_insert('rotation_euler', frame=f0 + 16)
for loc, f0 in (((-0.25, -0.3, 2.25), 97), ((0.3, -0.2, 1.95), 106), ((0.05, -0.3, 2.6), 146), ((-0.35, -0.25, 1.9), 206), ((0.28, -0.3, 2.4), 216)):
    star(loc, f0)

# light: one hard spot from above through a little haze, warm rim lights on the curtain
spot('spot', (0.8, -1.5, 8.5), 3200, (0, 0, 1.6), angle=24, blend=0.25, color=(1.0, 0.95, 0.88), radius=0.08)
area('curtainL', (-7, 1, 1.0), 2.5, 110, (1.0, 0.25, 0.3), (-4, 5.5, 3.5))
area('curtainR', (7, 1, 1.0), 2.5, 110, (0.9, 0.2, 0.5), (4, 5.5, 3.5))
area('front', (0, -7, 2.2), 3, 12, (0.9, 0.9, 1.0), (0, 0, 1.4))
haze = box('haze', (9, 9, 9.5), (0, 0, 4.7), None)
hm = bpy.data.materials.new('haze')
try: hm.use_nodes = True
except Exception: pass
nt = hm.node_tree
for n in list(nt.nodes):
    if n.type != 'OUTPUT_MATERIAL': nt.nodes.remove(n)
vs = nt.nodes.new('ShaderNodeVolumeScatter'); vs.inputs['Density'].default_value = 0.014
nt.links.new(vs.outputs[0], nt.nodes['Material Output'].inputs['Volume'])
haze.data.materials.append(hm)

cam = camera((0, -9, 2.2), (0, 0, 1.75), lens=50, fstop=4.0, focus=(0, -0.9, 1.6))
cam_move(cam, (0.5, -10.5, 2.5), (0, 0, 1.8), (-0.3, -8.4, 2.35), (0, 0, 1.95))

setup_render(samples=64, exposure=0.0)
bpy.context.scene.cycles.volume_bounces = 0
finish()

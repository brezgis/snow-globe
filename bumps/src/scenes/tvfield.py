"""tvfield: a television left on in a snowy field overnight."""
import bpy, math, os, random, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

s = reset()
world((0.006, 0.009, 0.02), 1.0)
rng = random.Random(5)

# snowfield with soft drifts
bpy.ops.mesh.primitive_grid_add(x_subdivisions=160, y_subdivisions=160, size=60, location=(0, 12, 0))
ground = bpy.context.object
gm = mat('snowfield', (0.86, 0.9, 1.0), 0.6)
ground.data.materials.append(gm)
tex = bpy.data.textures.new('drift', 'CLOUDS'); tex.noise_scale = 3.5; tex.noise_depth = 3
dm = ground.modifiers.new('drift', 'DISPLACE'); dm.texture = tex; dm.strength = 0.9; dm.mid_level = 0.55
for p in ground.data.polygons: p.use_smooth = True

# a treeline on the horizon
dark = mat('treeline', (0.004, 0.006, 0.008), 1.0)
for i in range(70):
    x = rng.uniform(-34, 34); y = rng.uniform(24, 34); h = rng.uniform(2.2, 4.6)
    cyl('tree', h * 0.26, h, (x, y, h / 2 + 0.2), dark, r2=0.0, verts=7, smooth=False)

# the set
T = empty('tv', (0, 0, -0.3))
T.rotation_euler = (math.radians(-3), math.radians(2.5), math.radians(-14))
case_m = noise_color(mat('case', rough=0.45, coat=0.2), (0.07, 0.035, 0.02), (0.16, 0.08, 0.04), scale=2.5, stretch=(12, 1, 1))
box('case', (1.5, 1.05, 1.12), (0, 0, 0.72), case_m, bevel=0.05, parent=T)
box('bezel', (1.02, 0.06, 0.84), (-0.17, -0.53, 0.74), mat('bezel', (0.02, 0.02, 0.02), 0.35), bevel=0.03, parent=T)
box('panel', (0.3, 0.04, 0.84), (0.52, -0.535, 0.74), mat('panel', (0.09, 0.085, 0.08), 0.4, metal=0.6), bevel=0.015, parent=T)
for k, z in enumerate((1.0, 0.78)):
    cyl('knob', 0.075, 0.07, (0.52, -0.58, z), mat('knob%d' % k, (0.02, 0.02, 0.02), 0.3), rot=(math.radians(90), 0, 0), parent=T, bevel=0.01)
for k in range(5):
    box('grille', (0.2, 0.012, 0.012), (0.52, -0.56, 0.42 + k * 0.045), mat('gr%d' % k, (0.01, 0.01, 0.01), 0.5), parent=T)
for dx in (-0.6, 0.6):
    for dy in (-0.38, 0.38):
        cyl('foot', 0.04, 0.2, (dx, dy, 0.08), mat('foot', (0.02, 0.02, 0.02)), r2=0.025, verts=12, parent=T)
# rabbit ears
cyl('earbase', 0.09, 0.05, (0.1, 0.1, 1.3), mat('eb', (0.02, 0.02, 0.02), 0.3), parent=T)
chrome = mat('chrome', (0.8, 0.8, 0.82), 0.2, metal=1.0)
for sgn in (-1, 1):
    e = cyl('ear', 0.008, 1.3, (0.1 + sgn * 0.36, 0.1, 1.85), chrome, verts=8, parent=T)
    e.rotation_euler = (0, math.radians(sgn * 33), 0)

# screen: colour bars, drawn here so nothing is downloaded
Wp, Hp = 320, 240
px = np.zeros((Hp, Wp, 4), dtype=np.float32); px[..., 3] = 1
bars = [(0.75, 0.75, 0.75), (0.75, 0.75, 0), (0, 0.75, 0.75), (0, 0.75, 0), (0.75, 0, 0.75), (0.75, 0, 0), (0, 0, 0.75)]
for i, c in enumerate(bars):
    px[int(Hp * 0.3):, int(i * Wp / 7):int((i + 1) * Wp / 7), :3] = c
low = [(0, 0, 0.75), (0.03, 0.03, 0.03), (0.75, 0, 0.75), (0.03, 0.03, 0.03), (0, 0.75, 0.75), (0.03, 0.03, 0.03), (0.75, 0.75, 0.75)]
for i, c in enumerate(low):
    px[int(Hp * 0.22):int(Hp * 0.3), int(i * Wp / 7):int((i + 1) * Wp / 7), :3] = c
for i, c in enumerate([(0, 0.05, 0.2), (1, 1, 1), (0.1, 0, 0.3), (0.02, 0.02, 0.02), (0.02, 0.02, 0.02), (0.02, 0.02, 0.02)]):
    px[:int(Hp * 0.22), int(i * Wp / 6):int((i + 1) * Wp / 6), :3] = c
img = bpy.data.images.new('bars', Wp, Hp)
img.pixels.foreach_set(px.ravel())
scr_m = mat('screen', (0, 0, 0), 0.15)
nt = scr_m.node_tree
tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = img; tn.interpolation = 'Linear'
nt.links.new(tn.outputs['Color'], bsdf(scr_m).inputs['Emission Color'])
es = bsdf(scr_m).inputs['Emission Strength']
bpy.ops.mesh.primitive_grid_add(x_subdivisions=16, y_subdivisions=12, size=1, location=(-0.17, -0.565, 0.74), rotation=(math.radians(90), 0, 0))
scr = bpy.context.object; scr.scale = (0.86, 0.68, 1); scr.parent = T
scr.data.materials.append(scr_m)
# bulge the tube a little
for v in scr.data.vertices:
    v.co.z += 0.045 * (1 - (v.co.x * 2) ** 2) * (1 - (v.co.y * 2) ** 2)
for p in scr.data.polygons: p.use_smooth = True
# flicker
frng = random.Random(9)
for f in range(1, FRAMES + 1, 2):
    es.default_value = 2.4 * (1 + frng.uniform(-0.07, 0.07)) * (0.72 if frng.random() < 0.03 else 1)
    es.keyframe_insert('default_value', frame=f)
# the glow the picture throws on the snow (helps the path tracer; the screen also lights for real)
gl = area('glow', (-0.25, -1.3, 0.75), 0.9, 16, (0.7, 0.8, 0.95), (-0.5, -4.0, 0.0), shape='RECTANGLE')
gl.parent = None

# moon, from behind and to the left
area('moon', (-14, 22, 16), 6, 1100, (0.55, 0.68, 1.0), (0, 0, 0))
area('skyfill', (6, -10, 12), 14, 120, (0.3, 0.4, 0.75), (0, 0, 0))

snowfall(700, ((-7, 7), (-6, 6), (-0.1, 6.0)), flake_r=0.011, fall=(0.5, 1.0), seed=21, sway=0.5,
         material=mat('flake', (1, 1, 1), 0.8, emit=(0.8, 0.88, 1.0), emit_strength=0.35))

cam = camera((2.2, -9.0, 1.25), (0, 0, 0.85), lens=40, fstop=2.8, focus=(0, -0.5, 0.8))
cam_move(cam, (2.6, -10.5, 1.3), (-0.6, 0, 1.05), (1.9, -7.4, 1.15), (-0.3, 0, 0.95))
cam.data.dof.focus_object = empty('focus', (0, -0.55, 0.8))

setup_render(samples=48, exposure=0.6)
finish()

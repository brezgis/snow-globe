"""station: the whole station, in a snow globe, on a shelf."""
import bpy, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

s = reset()
world((0.004, 0.005, 0.008))
rng = random.Random(3)

# shelf and wall
wood = noise_color(mat('wood', rough=0.42, coat=0.25), (0.11, 0.045, 0.018), (0.24, 0.11, 0.045), scale=3.0, stretch=(1, 14, 1), rough_var=0.08)
box('shelf', (9, 2.6, 0.18), (0, 0.3, -0.09), wood, bevel=0.02)
wall = noise_color(mat('wall', rough=0.9), (0.035, 0.045, 0.055), (0.05, 0.06, 0.07), scale=40)
plane('wall', 14, (0, 1.7, 2), wall, rot=(math.radians(90), 0, 0))

# a few books leaning at the left, out of focus
for i, (w, h, c) in enumerate([(0.22, 1.5, (0.25, 0.05, 0.04)), (0.3, 1.75, (0.05, 0.12, 0.2)), (0.18, 1.35, (0.5, 0.42, 0.25)), (0.26, 1.6, (0.06, 0.16, 0.1))]):
    box('book%d' % i, (w, 1.1, h), (-3.3 + i * 0.31, 0.9, h / 2), mat('bk%d' % i, c, 0.7), bevel=0.012, rot=(0, math.radians(-2 if i < 3 else -9), 0))
# a mug on the right, out of focus
cyl('mug', 0.34, 0.72, (2.75, 0.75, 0.36), mat('mug', (0.75, 0.72, 0.66), 0.25), bevel=0.03)

# the globe
base_m = mat('base', (0.035, 0.03, 0.028), 0.3, coat=0.5)
cyl('base', 0.84, 0.44, (0, 0, 0.22), base_m, r2=0.69, bevel=0.02)
cyl('lip', 0.7, 0.05, (0, 0, 0.455), mat('brass', (0.8, 0.6, 0.3), 0.3, metal=1.0), bevel=0.01)
G = (0, 0, 1.18)  # globe centre
glass = mat('glass', (1, 1, 1), 0.0, transmission=1.0, ior=1.45)
g = sphere('glass', 1.0, G, glass, segs=96, rings=48)
sol = g.modifiers.new('shell', 'SOLIDIFY'); sol.thickness = 0.02
g.visible_shadow = False   # let the lamps light the snow inside

# inside: a snowy hill, a house, a transmitter, trees
snow_m = mat('snowground', (0.92, 0.95, 1.0), 0.75)
sphere('hill', 1.0, (0, 0, 0.47), snow_m, scale=(0.69, 0.69, 0.33))
hx, hy, hz = -0.2, 0.0, 0.765
box('house', (0.34, 0.28, 0.2), (hx, hy, hz + 0.1), mat('housewall', (0.55, 0.16, 0.12), 0.8), bevel=0.004)
roof = cyl('roof', 0.24, 0.3, (hx, hy, hz + 0.275), mat('roof', (0.9, 0.93, 1.0), 0.8), rot=(math.radians(90), 0, 0), verts=3, smooth=False)
roof.scale = (1.0, 0.62, 1.0)
win = mat('window', (1, 0.7, 0.3), emit=(1.0, 0.62, 0.22), emit_strength=9)
box('win1', (0.07, 0.01, 0.07), (hx - 0.08, hy - 0.142, hz + 0.11), win)
box('win2', (0.07, 0.01, 0.07), (hx + 0.08, hy - 0.142, hz + 0.11), win)
box('door', (0.05, 0.01, 0.1), (hx, hy - 0.142, hz + 0.05), mat('door', (0.12, 0.06, 0.03), 0.6))
box('chimney', (0.05, 0.05, 0.12), (hx + 0.1, hy + 0.04, hz + 0.33), mat('chim', (0.3, 0.1, 0.08), 0.8))
point('houseglow', (hx, hy - 0.3, hz + 0.1), 0.35, (1.0, 0.6, 0.25), 0.05)

# transmitter mast: lattice of thin struts, red light on top
steel = mat('steel', (0.75, 0.2, 0.15), 0.5, metal=0.3)
tx, ty, tz, th = 0.27, 0.1, 0.73, 0.95
for dx, dy in ((-1, -1), (1, -1), (0, 1.2)):
    c = cyl('leg', 0.008, th, (tx + dx * 0.03, ty + dy * 0.03, tz + th / 2), steel, verts=8)
    c.rotation_euler = (math.radians(3.6 * dy), math.radians(-3.6 * dx), 0)
for k in range(1, 7):
    z = tz + th * k / 7
    w = 0.06 * (1 - k / 8)
    cyl('ring', w, 0.008, (tx, ty, z), steel, verts=3, smooth=False)
cyl('spike', 0.006, 0.16, (tx, ty, tz + th + 0.07), steel, verts=8)
beacon_m = mat('beacon', (1, 0.1, 0.05), emit=(1, 0.06, 0.03), emit_strength=40)
beacon = sphere('beacon', 0.022, (tx, ty, tz + th + 0.16), beacon_m, segs=16, rings=8)
bl = point('beaconlight', (tx, ty, tz + th + 0.16), 1.2, (1, 0.1, 0.05), 0.02)
# blink once every two seconds
es = bsdf(beacon_m).inputs['Emission Strength']
for f in range(1, FRAMES + 1, 48):
    for df, on in ((0, False), (3, True), (14, True), (17, False)):
        es.default_value = 40 if on else 0.5
        es.keyframe_insert('default_value', frame=f + df)
        bl.data.energy = 1.2 if on else 0.0
        bl.data.keyframe_insert('energy', frame=f + df)

pine = mat('pine', (0.03, 0.12, 0.07), 0.8)
for (x, y, z, h) in ((0.47, -0.18, 0.67, 0.26), (-0.5, -0.12, 0.66, 0.3), (-0.38, 0.34, 0.66, 0.36), (0.1, 0.42, 0.68, 0.3), (0.5, 0.2, 0.66, 0.24), (0.04, -0.4, 0.7, 0.18)):
    cyl('trunk', 0.012, 0.06, (x, y, z + 0.03), mat('trunk', (0.1, 0.05, 0.02)), verts=8)
    for k in range(3):
        cyl('pine', 0.11 * (1 - k * 0.24) * h / 0.3, h * 0.5, (x, y, z + 0.05 + h * (0.25 + k * 0.22)), pine, r2=0.0, verts=12, smooth=False)

# snow inside the glass (kept inside a cylinder that fits in the sphere)
def inside(r):
    while True:
        x, y = r.uniform(-0.8, 0.8), r.uniform(-0.8, 0.8)
        d2 = x * x + y * y
        if d2 < 0.78 * 0.78: break
    top = math.sqrt(0.95 * 0.95 - d2)
    if d2 > 0.6 * 0.6: return x, y, G[2] + top * 0.95, G[2] - top * 0.6
    return x, y, G[2] + top * 0.95, 0.47 + 0.33 * math.sqrt(max(0.0, 1 - d2 / 0.476))
snowfall(340, inside, flake_r=0.006, fall=(0.11, 0.26), seed=11, sway=0.05,
         material=mat('flake', (1, 1, 1), 0.8, emit=(1, 1, 1), emit_strength=0.5))

# light: a warm lamp off to the right, cool fill from the left, rim from behind
area('key', (3.2, -2.6, 3.4), 1.6, 110, (1.0, 0.82, 0.62), G)
fill = area('fill', (-3.5, -2.2, 1.6), 2.0, 25, (0.55, 0.7, 1.0), G)
top = area('top', (0, -0.2, 3.6), 0.9, 22, (0.7, 0.82, 1.0), G)
rim = area('rim', (-1.6, 1.4, 2.6), 1.0, 45, (0.7, 0.85, 1.0), G)
area('walllight', (2.6, 0.2, 3.3), 1.5, 45, (1.0, 0.7, 0.45), (1.5, 1.7, 1.2))

cam = camera((0.9, -6.6, 1.55), (0, 0, 1.12), lens=62, fstop=2.2, focus=(0, -0.3, 1.1))
cam_move(cam, (1.5, -9.2, 1.9), (0.1, 0, 1.0), (-0.35, -7.0, 1.55), (0, 0, 1.12))
cam.data.dof.focus_object = empty('focus', (0, -0.2, 1.1))

for l in (top, rim, fill):
    l.visible_glossy = False; l.visible_transmission = False
setup_render(samples=64, exposure=0.3)
finish()

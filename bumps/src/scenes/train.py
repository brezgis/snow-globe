"""train: a toy train on a table. One lap takes six seconds."""
import bpy, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

s = reset()
world((0.004, 0.004, 0.006))
rng = random.Random(6)
R = 3.0

wood = noise_color(mat('table', rough=0.4, coat=0.25), (0.13, 0.06, 0.025), (0.26, 0.13, 0.055), scale=1.5, stretch=(1, 12, 1), rough_var=0.07)
box('table', (14, 11, 0.3), (0, 0, -0.15), wood, bevel=0.04)
felt = noise_color(mat('felt', rough=0.95), (0.03, 0.16, 0.06), (0.05, 0.23, 0.09), scale=60)
cyl('mat', 4.3, 0.03, (0, 0, 0.015), felt, verts=96)

# track
rail = mat('rail', (0.6, 0.6, 0.62), 0.25, metal=1.0)
tie = mat('tie', (0.14, 0.08, 0.04), 0.7)
for rr in (R - 0.13, R + 0.13):
    bpy.ops.mesh.primitive_torus_add(major_radius=rr, minor_radius=0.018, major_segments=160, minor_segments=8, location=(0, 0, 0.085))
    t = bpy.context.object; t.data.materials.append(rail)
    for p in t.data.polygons: p.use_smooth = True
for k in range(72):
    a = 2 * math.pi * k / 72
    box('tie', (0.42, 0.07, 0.035), (R * math.cos(a), R * math.sin(a), 0.05), tie, rot=(0, 0, a))

# the train: every car hangs off a pivot at the centre of the loop
def car(angle):
    piv = empty('pivot', (0, 0, 0))
    piv.rotation_euler = (0, 0, angle)
    body = empty('car', (R, 0, 0.1), parent=piv)   # +Y of this empty is the direction of travel (clockwise seen from above is -Y)
    return piv, body

red = mat('red', (0.75, 0.04, 0.03), 0.3, coat=0.5)
blue = mat('blue', (0.03, 0.12, 0.5), 0.3, coat=0.5)
yellow = mat('yellow', (0.9, 0.62, 0.05), 0.3, coat=0.5)
green = mat('green', (0.04, 0.35, 0.12), 0.3, coat=0.5)
black = mat('black', (0.015, 0.015, 0.015), 0.35)
brass = mat('brass', (0.9, 0.65, 0.25), 0.25, metal=1.0)

def wheels(parent, ys, r=0.085):
    for y in ys:
        for x in (-0.13, 0.13):
            cyl('wheel', r, 0.03, (x, y, r - 0.015), black, rot=(0, math.radians(90), 0), verts=20, parent=parent)

pivots = []
# engine (travels toward -Y in its own frame; pivot rotation is negative, i.e. clockwise)
piv, e = car(0.0); pivots.append(piv)
box('frame', (0.24, 0.72, 0.06), (0, 0, 0.12), black, bevel=0.01, parent=e)
cyl('boiler', 0.115, 0.44, (0, -0.1, 0.27), red, rot=(math.radians(90), 0, 0), verts=32, parent=e)
box('cab', (0.25, 0.22, 0.3), (0, 0.24, 0.3), red, bevel=0.015, parent=e)
box('cabroof', (0.29, 0.27, 0.035), (0, 0.24, 0.465), black, bevel=0.012, parent=e)
cyl('stack', 0.04, 0.16, (0, -0.24, 0.43), black, r2=0.06, verts=16, parent=e)
cyl('dome', 0.05, 0.07, (0, -0.06, 0.4), brass, verts=16, parent=e)
cyl('nose', 0.117, 0.03, (0, -0.33, 0.27), black, rot=(math.radians(90), 0, 0), verts=32, parent=e)
sphere('lamp', 0.035, (0, -0.35, 0.36), mat('lamp', (1, 0.9, 0.6), emit=(1, 0.85, 0.5), emit_strength=12), segs=12, rings=6, parent=e)
wheels(e, (-0.22, 0.0, 0.24))
# wagons
for k, (col, load) in enumerate(((blue, yellow), (green, None), (yellow, red))):
    piv, c = car(0.29 * (k + 1)); pivots.append(piv)
    box('wframe', (0.22, 0.6, 0.05), (0, 0, 0.11), black, bevel=0.01, parent=c)
    box('wbody', (0.25, 0.56, 0.17), (0, 0, 0.22), col, bevel=0.015, parent=c)
    if load:
        for j in range(3):
            cyl('load', 0.05, 0.5, (-0.06 + 0.06 * j, 0, 0.34 + (0.045 if j == 1 else 0)), load, rot=(math.radians(90), 0, 0), verts=12, parent=c)
    wheels(c, (-0.18, 0.18))

# two laps in twelve seconds, clockwise; the engine is nearest the camera at 1.5 s and 7.5 s
theta0 = math.radians(-52 + 90)
for piv in pivots:
    a0 = piv.rotation_euler.z + theta0
    piv.rotation_euler = (0, 0, a0); piv.keyframe_insert('rotation_euler', frame=1)
    piv.rotation_euler = (0, 0, a0 - 4 * math.pi); piv.keyframe_insert('rotation_euler', frame=FRAMES + 1)

# scenery
pine = mat('pine', (0.02, 0.2, 0.08), 0.6)
trunk = mat('trunk', (0.2, 0.1, 0.04), 0.7)
for (x, y, h) in ((0.5, 0.9, 0.9), (-0.7, 0.3, 1.1), (-0.2, -0.9, 0.7), (1.2, -0.3, 0.8), (-1.4, -0.9, 0.9), (0.9, 1.6, 0.65),
                  (-3.7, 1.4, 0.8), (3.6, 1.9, 0.9), (-3.5, -1.7, 0.7)):
    cyl('trunk', 0.05, 0.2, (x, y, 0.1), trunk, verts=10)
    for k in range(3):
        cyl('pine', 0.2 * h * (1 - 0.25 * k), 0.34 * h, (x, y, 0.2 + h * 0.66 * (0.25 + 0.24 * k)), pine, r2=0.0, verts=14, smooth=False)
# a station
box('platform', (1.3, 0.5, 0.06), (0.1, 2.25, 0.06), mat('plat', (0.5, 0.48, 0.45), 0.7), bevel=0.01)
box('stn', (0.8, 0.34, 0.36), (0.1, 2.2, 0.27), mat('stn', (0.85, 0.8, 0.68), 0.6), bevel=0.01)
roof = cyl('stnroof', 0.3, 1.0, (0.1, 2.2, 0.52), red, rot=(0, math.radians(90), 0), verts=3, smooth=False)
roof.scale = (0.55, 1.0, 1.0); roof.rotation_euler = (math.radians(90), 0, math.radians(90))
box('stnwin', (0.16, 0.01, 0.14), (-0.1, 2.025, 0.3), mat('stnwin', (1, 0.8, 0.4), emit=(1, 0.7, 0.3), emit_strength=6))
box('stnwin2', (0.16, 0.01, 0.14), (0.3, 2.025, 0.3), mat('stnwin2', (1, 0.8, 0.4), emit=(1, 0.7, 0.3), emit_strength=6))
cyl('pond', 0.7, 0.012, (-1.2, 1.3, 0.04), mat('pond', (0.02, 0.1, 0.25), 0.05), verts=40).scale = (1.3, 0.8, 1)

# a desk lamp somewhere above right; the rest of the room is dark
area('lamp', (5.5, -3.5, 7.5), 2.2, 900, (1.0, 0.8, 0.58), (0, 0, 0))
area('fill', (-7, -5, 3), 5, 30, (0.45, 0.6, 1.0), (0, 0, 0.3))
area('back', (-2, 8, 4), 3, 160, (1.0, 0.7, 0.5), (0, 0, 0.3))

cam = camera((5.6, -7.2, 3.3), (0.2, -0.4, 0.2), lens=58, fstop=2.4, focus=(1.8, -2.4, 0.2))
cam_move(cam, (5.8, -7.4, 3.4), (0.2, -0.5, 0.2), (5.2, -6.9, 3.0), (0.2, -0.4, 0.2))
cam.data.dof.focus_object = empty('focus', (1.6, -2.3, 0.2))

setup_render(samples=48, exposure=0.0)
finish()

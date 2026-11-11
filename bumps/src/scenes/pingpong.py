"""pingpong: an empty room, then four hundred ping pong balls.

Built at 10x scale (1 unit = 10 cm, gravity scaled to match) so the rigid
body solver is comfortable with 4 cm balls.
"""
import bpy, math, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *

s = reset()
world((0.02, 0.02, 0.025))
rng = random.Random(4)
RELEASE = 96          # frame the first balls let go (4.0 s, the second card)

floor_m = noise_color(mat('floor', rough=0.35, coat=0.3), (0.2, 0.1, 0.045), (0.34, 0.19, 0.09), scale=1.2, stretch=(1, 9, 1), rough_var=0.06)
wall_m = mat('wall', (0.42, 0.4, 0.36), 0.85)
floor = box('floor', (44, 44, 1), (0, -4, -0.5), floor_m)
back = box('back', (44, 1, 34), (0, 16.5, 17), wall_m)
left = box('left', (1, 44, 34), (-21.5, -4, 17), wall_m)
right = box('right', (1, 44, 34), (21.5, -4, 17), wall_m)
trim = mat('trim', (0.8, 0.78, 0.72), 0.5)
box('base1', (42, 0.25, 1.1), (0, 15.9, 0.55), trim, bevel=0.05)
box('base2', (0.25, 42, 1.1), (-20.9, -4, 0.55), trim, bevel=0.05)
box('base3', (0.25, 42, 1.1), (20.9, -4, 0.55), trim, bevel=0.05)
# an outlet, for scale
box('outlet', (0.7, 0.08, 1.15), (9, 15.95, 3.2), mat('outlet', (0.85, 0.84, 0.8), 0.4), bevel=0.05)

# one stool in the middle of the room
wood = noise_color(mat('stool', rough=0.4, coat=0.3), (0.3, 0.17, 0.07), (0.5, 0.3, 0.13), scale=2, stretch=(1, 8, 1))
seat = cyl('seat', 1.7, 0.35, (0, 2, 4.6), wood, bevel=0.08)
legs = []
for k in range(3):
    a = math.radians(90 + 120 * k)
    l = cyl('leg', 0.16, 4.7, (1.25 * math.cos(a), 2 + 1.25 * math.sin(a), 2.3), wood, verts=16)
    l.rotation_euler = (math.radians(9) * math.sin(a), -math.radians(9) * math.cos(a), 0)
    legs.append(l)

# the balls
white = mat('ball', (0.93, 0.93, 0.9), 0.38)
orange = mat('ballo', (0.95, 0.38, 0.05), 0.38)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, segments=20, ring_count=10)
proto = bpy.context.object
for p in proto.data.polygons: p.use_smooth = True
mesh_w = proto.data; mesh_w.materials.append(white)
mesh_o = mesh_w.copy(); mesh_o.materials.clear(); mesh_o.materials.append(orange)
bpy.data.objects.remove(proto)

s.gravity = (0, 0, -98.1)
bpy.ops.rigidbody.world_add()
rbw = s.rigidbody_world
rbw.substeps_per_frame = 12
rbw.solver_iterations = 12
rbw.point_cache.frame_start = 1
rbw.point_cache.frame_end = FRAMES
if rbw.collection is None:
    rbw.collection = bpy.data.collections.new('rb')

def passive(o, shape='BOX', bounce=0.82, friction=0.5):
    rbw.collection.objects.link(o)
    o.rigid_body.type = 'PASSIVE'
    o.rigid_body.collision_shape = shape
    o.rigid_body.restitution = bounce
    o.rigid_body.friction = friction

for o in (floor, back, left, right): passive(o)
passive(seat, 'CONVEX_HULL', 0.8)
for l in legs: passive(l, 'CONVEX_HULL', 0.7)
# an invisible wall behind the camera keeps them in the room
front = box('front', (44, 1, 34), (0, -26.5, 17), None); front.hide_render = True; passive(front)

balls = []
for i in range(10):
    for j in range(8):
        for k in range(5):
            o = bpy.data.objects.new('ball', mesh_o if rng.random() < 0.14 else mesh_w)
            s.collection.objects.link(o)
            o.location = (-9 + i * 2 + rng.uniform(-0.6, 0.6), -5 + j * 1.9 + rng.uniform(-0.6, 0.6), 27 + k * 1.6 + rng.uniform(-0.4, 0.4))
            rbw.collection.objects.link(o)
            rb = o.rigid_body
            rb.collision_shape = 'SPHERE'; rb.mass = 0.3
            rb.restitution = 0.88; rb.friction = 0.35
            rb.linear_damping = 0.06; rb.angular_damping = 0.25
            rb.use_deactivation = False
            go = RELEASE + int(k * 7 + rng.uniform(0, 22))
            rb.kinematic = True; rb.keyframe_insert('kinematic', frame=go - 1)
            rb.kinematic = False; rb.keyframe_insert('kinematic', frame=go)
            balls.append(o)

s.frame_set(1)
with bpy.context.temp_override(scene=s, point_cache=rbw.point_cache):
    bpy.ops.ptcache.bake(bake=True)

# light: a window somewhere off to the left, a dull ceiling fixture
area('window', (-17, -14, 20), 12, 30000, (1.0, 0.9, 0.76), (2, 4, 2), shape='RECTANGLE')
area('ceiling', (2, -2, 31), 16, 5000, (0.8, 0.88, 1.0), (0, 0, 0))

cam = camera((0, -25.0, 13), (0, 2, 6.5), lens=30)
cam_move(cam, (0.6, -25.3, 13.2), (0, 2, 6.8), (-0.6, -23.5, 12.2), (0, 2, 6.0))

setup_render(samples=48, exposure=0.0)
finish(linear=False)

"""Shared helpers for the snow-globe bump scenes (Blender 5.x, Cycles).

Each scene script builds its scene from nothing and calls finish(), which
reads the command line:

  blender -b --python scenes/<name>.py -- --out DIR            # all 288 frames
  blender -b --python scenes/<name>.py -- --out DIR --still 1,120,288 --samples 24

Frames are written as JPEGs: DIR/0001.jpg ... DIR/0288.jpg (1280x720, 24 fps).
"""
import bpy, math, os, random, sys
from mathutils import Vector

FPS, FRAMES, W, H = 24, 288, 1280, 720


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.frame_start, s.frame_end = 1, FRAMES
    s.render.fps = FPS
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    w = bpy.data.worlds.new('world')
    try: w.use_nodes = True
    except Exception: pass
    s.world = w
    return s


def world(color=(0, 0, 0), strength=1.0):
    bg = bpy.context.scene.world.node_tree.nodes.get('Background')
    bg.inputs[0].default_value = (*color, 1)
    bg.inputs[1].default_value = strength


def mat(name, color=(0.8, 0.8, 0.8), rough=0.5, metal=0.0, emit=None, emit_strength=1.0,
        transmission=0.0, ior=1.45, coat=0.0, alpha=1.0, spec=None):
    m = bpy.data.materials.new(name)
    try: m.use_nodes = True
    except Exception: pass
    b = m.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*color, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Transmission Weight'].default_value = transmission
    b.inputs['IOR'].default_value = ior
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Alpha'].default_value = alpha
    if spec is not None:
        b.inputs['Specular IOR Level'].default_value = spec
    if emit is not None:
        b.inputs['Emission Color'].default_value = (*emit, 1)
        b.inputs['Emission Strength'].default_value = emit_strength
    return m


def bsdf(m):
    return m.node_tree.nodes.get('Principled BSDF')


def noise_color(m, c1, c2, scale=8.0, stretch=(1, 1, 1), detail=4.0, rough_var=0.0):
    """Drive a material's base color from stretched noise (wood, felt, plaster)."""
    nt = m.node_tree
    tc = nt.nodes.new('ShaderNodeTexCoord')
    mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = stretch
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = scale
    nz.inputs['Detail'].default_value = detail
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.3
    ramp.color_ramp.elements[0].color = (*c1, 1)
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[1].color = (*c2, 1)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], nz.inputs['Vector'])
    nt.links.new(nz.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], bsdf(m).inputs['Base Color'])
    if rough_var:
        mr = nt.nodes.new('ShaderNodeMapRange')
        mr.inputs['To Min'].default_value = bsdf(m).inputs['Roughness'].default_value - rough_var
        mr.inputs['To Max'].default_value = bsdf(m).inputs['Roughness'].default_value + rough_var
        nt.links.new(nz.outputs[0], mr.inputs['Value'])
        nt.links.new(mr.outputs[0], bsdf(m).inputs['Roughness'])
    return m


def _finish_obj(o, material, smooth, bevel, parent):
    if material: o.data.materials.append(material)
    if smooth:
        for p in o.data.polygons: p.use_smooth = True
    if bevel:
        bm = o.modifiers.new('bevel', 'BEVEL')
        bm.width = bevel; bm.segments = 3; bm.limit_method = 'ANGLE'
    if parent: o.parent = parent
    return o


def box(name, size, loc=(0, 0, 0), material=None, bevel=0.0, rot=(0, 0, 0), parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name
    o.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    return _finish_obj(o, material, bool(bevel), bevel, parent)


def cyl(name, r, depth, loc=(0, 0, 0), material=None, rot=(0, 0, 0), verts=48, r2=None,
        bevel=0.0, smooth=True, parent=None):
    if r2 is None:
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, vertices=verts, location=loc, rotation=rot)
    else:
        bpy.ops.mesh.primitive_cone_add(radius1=r, radius2=r2, depth=depth, vertices=verts, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name
    o = _finish_obj(o, material, smooth, bevel, parent)
    if smooth:
        try:
            m = o.modifiers.new('wn', 'WEIGHTED_NORMAL')
        except Exception: pass
        try: bpy.ops.object.shade_auto_smooth(angle=math.radians(40))
        except Exception: pass
    return o


def sphere(name, r, loc=(0, 0, 0), material=None, segs=48, rings=24, scale=(1, 1, 1), parent=None, ico=0):
    if ico:
        bpy.ops.mesh.primitive_ico_sphere_add(radius=r, subdivisions=ico, location=loc)
    else:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=segs, ring_count=rings, location=loc)
    o = bpy.context.object; o.name = name
    o.scale = scale
    return _finish_obj(o, material, True, 0, parent)


def plane(name, size, loc=(0, 0, 0), material=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_plane_add(size=size, location=loc, rotation=rot)
    o = bpy.context.object; o.name = name
    if material: o.data.materials.append(material)
    return o


def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    if parent: o.parent = parent
    return o


def area(name, loc, size, power, color=(1, 1, 1), target=(0, 0, 0), shape='DISK', size_y=None, spread=None):
    l = bpy.data.lights.new(name, 'AREA')
    l.energy = power; l.color = color; l.size = size; l.shape = shape
    if size_y: l.size_y = size_y
    if spread is not None: l.spread = spread
    o = bpy.data.objects.new(name, l)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    look(o, target)
    return o


def spot(name, loc, power, target=(0, 0, 0), angle=40, blend=0.3, color=(1, 1, 1), radius=0.05):
    l = bpy.data.lights.new(name, 'SPOT')
    l.energy = power; l.color = color; l.spot_size = math.radians(angle); l.spot_blend = blend
    l.shadow_soft_size = radius
    o = bpy.data.objects.new(name, l)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    look(o, target)
    return o


def point(name, loc, power, color=(1, 1, 1), radius=0.05):
    l = bpy.data.lights.new(name, 'POINT')
    l.energy = power; l.color = color; l.shadow_soft_size = radius
    o = bpy.data.objects.new(name, l)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    hide_from_camera(o)
    return o


def hide_from_camera(o):
    for a in ('visible_camera', 'visible_glossy', 'visible_transmission'):
        try: setattr(o, a, False)
        except Exception: pass
    return o


def look(o, target):
    d = Vector(target) - Vector(o.location)
    o.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def camera(loc, target, lens=50, fstop=None, focus=None):
    c = bpy.data.cameras.new('cam')
    c.lens = lens
    o = bpy.data.objects.new('cam', c)
    bpy.context.scene.collection.objects.link(o)
    o.location = loc
    look(o, target)
    if fstop:
        c.dof.use_dof = True
        c.dof.aperture_fstop = fstop
        c.dof.focus_distance = (Vector(focus if focus else target) - Vector(loc)).length
    bpy.context.scene.camera = o
    return o


def key(o, path, frame, value=None, index=-1):
    if value is not None:
        if index >= 0:
            v = getattr(o, path); v[index] = value
        else:
            setattr(o, path, value)
    o.keyframe_insert(path, frame=frame, index=index)


def ease(t):
    return t * t * (3 - 2 * t)


def cam_move(cam, loc_a, tgt_a, loc_b, tgt_b, f0=1, f1=FRAMES, steps=24, eased=True):
    """Keyframe a camera along a straight dolly, re-aiming at each step."""
    for i in range(steps + 1):
        t = i / steps
        k = ease(t) if eased else t
        f = round(f0 + (f1 - f0) * t)
        cam.location = Vector(loc_a).lerp(Vector(loc_b), k)
        look(cam, Vector(tgt_a).lerp(Vector(tgt_b), k))
        cam.keyframe_insert('location', frame=f)
        cam.keyframe_insert('rotation_euler', frame=f)


def snowfall(n, region, flake_r=0.012, fall=(0.25, 0.5), seed=7, material=None, sway=0.05, parent=None):
    """n flakes looping forever inside region=((x0,x1),(y0,y1),(z0,z1)).

    region may also be a function(rng) -> (x, y, ztop, zbottom) for odd shapes.
    Fall speed is in units per second. Every flake loops with its own phase.
    """
    rng = random.Random(seed)
    m = material or mat('snow', (1, 1, 1), 0.9, emit=(1, 1, 1), emit_strength=0.15)
    bpy.ops.mesh.primitive_ico_sphere_add(radius=1, subdivisions=1)
    proto = bpy.context.object
    mesh = proto.data; mesh.materials.append(m)
    bpy.data.objects.remove(proto)
    out = []
    for i in range(n):
        if callable(region):
            x, y, zt, zb = region(rng)
        else:
            (x0, x1), (y0, y1), (zb, zt) = region
            x, y = rng.uniform(x0, x1), rng.uniform(y0, y1)
        o = bpy.data.objects.new('flake', mesh)
        bpy.context.scene.collection.objects.link(o)
        if parent: o.parent = parent
        r = flake_r * rng.uniform(0.6, 1.4)
        o.scale = (r, r, r)
        speed = rng.uniform(*fall)
        period = max(8, round((zt - zb) / speed * FPS))
        phase = rng.randrange(period)
        sx, sy = rng.uniform(-sway, sway), rng.uniform(-sway, sway)
        f = 1 - phase
        while f <= FRAMES + 1:
            o.location = (x - sx, y - sy, zt); o.keyframe_insert('location', frame=f)
            o.location = (x + sx, y + sy, zb); o.keyframe_insert('location', frame=f + period - 1)
            f += period
        out.append(o)
    return out


def setup_render(samples=48, exposure=0.0, look_name=None, film_transparent=False):
    s = bpy.context.scene
    s.render.engine = 'CYCLES'
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for t in ('OPTIX', 'CUDA'):
        try:
            prefs.compute_device_type = t
            prefs.get_devices()
            for d in prefs.devices: d.use = (d.type == t)
            break
        except Exception as e:
            print('device', t, 'unavailable', e)
    s.cycles.device = 'GPU'
    s.cycles.samples = samples
    s.cycles.use_adaptive_sampling = True
    s.cycles.adaptive_threshold = 0.02
    s.cycles.use_denoising = True
    try: s.cycles.denoiser = 'OPTIX'
    except Exception: pass
    s.cycles.max_bounces = 6
    s.cycles.caustics_reflective = False
    s.cycles.caustics_refractive = False
    s.render.use_persistent_data = True
    s.render.resolution_x, s.render.resolution_y = W, H
    s.render.resolution_percentage = 100
    s.render.film_transparent = film_transparent
    s.view_settings.view_transform = 'Filmic' if 'Filmic' in [i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties['view_transform'].enum_items] else 'AgX'
    if look_name:
        try: s.view_settings.look = look_name
        except Exception as e: print('look unavailable', e)
    s.view_settings.exposure = exposure
    s.render.image_settings.file_format = 'JPEG'
    s.render.image_settings.quality = 94


def all_fcurves():
    for act in bpy.data.actions:
        try:
            for fc in act.fcurves: yield fc
            continue
        except Exception:
            pass
        for layer in act.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    for fc in cb.fcurves: yield fc


def linearize(skip=()):
    """Blender eases between keyframes by default. Everything here wants straight lines."""
    n = 0
    for fc in all_fcurves():
        if any(k in fc.data_path for k in skip): continue
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'
        n += 1
    print('linearized', n, 'fcurves')


def finish(linear=True):
    if linear: linearize()
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    opt = {'out': '/tmp/sg-render', 'still': '', 'samples': '', 'pct': ''}
    i = 0
    while i < len(argv):
        if argv[i].startswith('--') and i + 1 < len(argv):
            opt[argv[i][2:]] = argv[i + 1]; i += 2
        else: i += 1
    s = bpy.context.scene
    if opt['samples']: s.cycles.samples = int(opt['samples'])
    if opt['pct']: s.render.resolution_percentage = int(opt['pct'])
    os.makedirs(opt['out'], exist_ok=True)
    if opt['still']:
        for f in [int(x) for x in opt['still'].split(',')]:
            s.frame_set(f)
            s.render.filepath = os.path.join(opt['out'], 'still_%04d.jpg' % f)
            bpy.ops.render.render(write_still=True)
    else:
        s.render.filepath = os.path.join(opt['out'], '')
        s.render.use_file_extension = True
        # skip frames that already exist so an interrupted render can resume
        s.render.use_overwrite = False
        bpy.ops.render.render(animation=True)
    print('SG_DONE', opt['out'])

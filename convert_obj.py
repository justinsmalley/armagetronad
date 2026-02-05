#!/usr/bin/env python3
"""
Convert standard Wavefront OBJ to Armagetron format.

Handles:
- Coordinate transform (OBJ Y-up to game X-forward, Z-up)
- Triangulation of quads/ngons
- Scaling and centering
- Optionally splitting by bounding box regions
"""

import argparse
import sys


def parse_obj(filename):
    """Parse OBJ file, return vertices and faces."""
    vertices = []
    faces = []
    
    print(f"Parsing {filename}...")
    with open(filename, 'r') as f:
        for line_num, line in enumerate(f, 1):
            if line_num % 10000 == 0:
                print(f"  ...line {line_num}")
            
            line = line.strip()
            if line.startswith('v '):
                parts = line.split()
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                vertices.append((x, y, z))
            elif line.startswith('f '):
                parts = line.split()[1:]
                face = []
                for p in parts:
                    # Handle v/vt/vn format
                    v = p.split('/')[0]
                    face.append(int(v))
                faces.append(face)
    
    return vertices, faces


def triangulate(faces):
    """Convert quads/ngons to triangles using fan triangulation."""
    triangles = []
    for face in faces:
        if len(face) == 3:
            triangles.append(face)
        elif len(face) >= 4:
            for i in range(1, len(face) - 1):
                triangles.append([face[0], face[i], face[i + 1]])
    return triangles


def transform_vertex(v, scale=1.0):
    """
    Transform from OBJ coords to game coords.
    
    This OBJ has:
      Z = forward/back (truck length)
      X = left/right (truck width)
      Y = up (truck height)
    
    Game wants:
      X = forward
      Y = left/right
      Z = up
    
    Transform: game_X = obj_Z, game_Y = obj_X, game_Z = obj_Y
    """
    x, y, z = v
    return (z * scale, x * scale, y * scale)


def center_geometry(vertices, center_xy=True, floor_z=True):
    """Center geometry and put floor at z=0."""
    if not vertices:
        return vertices
    
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    zs = [v[2] for v in vertices]
    
    offset_x = (max(xs) + min(xs)) / 2 if center_xy else 0
    offset_y = (max(ys) + min(ys)) / 2 if center_xy else 0
    offset_z = min(zs) if floor_z else 0
    
    return [(x - offset_x, y - offset_y, z - offset_z) for x, y, z in vertices]


def write_mod_file(vertices, faces, filename):
    with open(filename, 'w') as f:
        for i, (x, y, z) in enumerate(vertices, 1):
            f.write(f"v {i}\t{x:.4f}\t{y:.4f}\t{z:.4f}\n")
        for face in faces:
            f.write(f"f \t{face[0]}\t{face[1]}\t{face[2]}\n")


def write_obj_file(vertices, faces, filename):
    with open(filename, 'w') as f:
        f.write("s 1\n")
        for x, y, z in vertices:
            f.write(f"v {x:.4f}\t{y:.4f}\t{z:.4f}\n")
        for face in faces:
            f.write(f"f \t{face[0]}\t{face[1]}\t{face[2]}\n")


def split_by_z(vertices, faces, z_threshold):
    """
    Split geometry by Z coordinate.
    Below threshold = wheels, above = body.
    """
    # Find which vertices are "low" (wheels)
    low_verts = set(i + 1 for i, v in enumerate(vertices) if v[2] < z_threshold)
    
    body_faces = []
    wheel_faces = []
    
    for face in faces:
        if all(v in low_verts for v in face):
            wheel_faces.append(face)
        else:
            body_faces.append(face)
    
    return body_faces, wheel_faces


def extract_part(all_verts, part_faces):
    """Extract a subset of geometry with renumbered vertices."""
    used = set()
    for f in part_faces:
        used.update(f)
    if not used:
        return [], []
    sorted_v = sorted(used)
    vmap = {old: new for new, old in enumerate(sorted_v, 1)}
    new_verts = [all_verts[v - 1] for v in sorted_v]
    new_faces = [[vmap[v] for v in f] for f in part_faces]
    return new_verts, new_faces


def main():
    parser = argparse.ArgumentParser(description='Convert OBJ to Armagetron format')
    parser.add_argument('input', help='Input OBJ file')
    parser.add_argument('--scale', type=float, default=0.1, help='Scale factor')
    parser.add_argument('--output-dir', default='models', help='Output directory')
    parser.add_argument('--body-only', action='store_true', help='Output as single body (no wheel split)')
    parser.add_argument('--wheel-z', type=float, default=None, help='Z threshold for wheel split (in game coords)')
    args = parser.parse_args()
    
    vertices, faces = parse_obj(args.input)
    print(f"  {len(vertices)} vertices, {len(faces)} faces")
    
    # Triangulate
    faces = triangulate(faces)
    print(f"  {len(faces)} triangles after triangulation")
    
    # Transform coordinates and scale
    vertices = [transform_vertex(v, args.scale) for v in vertices]
    
    # Center and floor
    vertices = center_geometry(vertices)
    
    # Get bounds
    xs = [v[0] for v in vertices]
    ys = [v[1] for v in vertices]
    zs = [v[2] for v in vertices]
    print(f"  Bounds: X[{min(xs):.2f}, {max(xs):.2f}] Y[{min(ys):.2f}, {max(ys):.2f}] Z[{min(zs):.2f}, {max(zs):.2f}]")
    
    if args.body_only:
        # Output everything as body
        print(f"\nWriting full model to {args.output_dir}/cycle_body...")
        write_mod_file(vertices, faces, f"{args.output_dir}/cycle_body.mod")
        write_obj_file(vertices, faces, f"{args.output_dir}/cycle_body.obj")
        
        # Write empty wheel files
        write_mod_file([], [], f"{args.output_dir}/cycle_front.mod")
        write_obj_file([], [], f"{args.output_dir}/cycle_front.obj")
        write_mod_file([], [], f"{args.output_dir}/cycle_rear.mod")
        write_obj_file([], [], f"{args.output_dir}/cycle_rear.obj")
    else:
        # Try to split wheels from body
        z_thresh = args.wheel_z if args.wheel_z else max(zs) * 0.15
        print(f"\nSplitting at Z={z_thresh:.2f}...")
        
        body_faces, wheel_faces = split_by_z(vertices, faces, z_thresh)
        
        body_v, body_f = extract_part(vertices, body_faces)
        wheel_v, wheel_f = extract_part(vertices, wheel_faces)
        
        print(f"  Body: {len(body_v)} verts, {len(body_f)} faces")
        print(f"  Wheels: {len(wheel_v)} verts, {len(wheel_f)} faces")
        
        # For wheels, split left/right by Y coordinate
        if wheel_v:
            wheel_y = [v[1] for v in wheel_v]
            y_center = (max(wheel_y) + min(wheel_y)) / 2
            
            # Also split by X for front/rear
            wheel_x = [v[0] for v in wheel_v]
            x_center = (max(wheel_x) + min(wheel_x)) / 2
            
            front_faces = []
            rear_faces = []
            
            for f in wheel_f:
                avg_x = sum(wheel_v[v-1][0] for v in f) / len(f)
                if avg_x > x_center:
                    front_faces.append(f)
                else:
                    rear_faces.append(f)
            
            front_v, front_f = extract_part(wheel_v, front_faces)
            rear_v, rear_f = extract_part(wheel_v, rear_faces)
            
            # Center wheels
            if front_v:
                front_v = center_geometry(front_v, center_xy=True, floor_z=False)
                # Center Z around 0
                zs = [v[2] for v in front_v]
                z_center = (max(zs) + min(zs)) / 2
                front_v = [(x, y, z - z_center) for x, y, z in front_v]
            
            if rear_v:
                rear_v = center_geometry(rear_v, center_xy=True, floor_z=False)
                zs = [v[2] for v in rear_v]
                z_center = (max(zs) + min(zs)) / 2
                rear_v = [(x, y, z - z_center) for x, y, z in rear_v]
            
            print(f"  Front wheels: {len(front_v)} verts, {len(front_f)} faces")
            print(f"  Rear wheels: {len(rear_v)} verts, {len(rear_f)} faces")
        else:
            front_v, front_f = [], []
            rear_v, rear_f = [], []
        
        print(f"\nWriting to {args.output_dir}/...")
        write_mod_file(body_v, body_f, f"{args.output_dir}/cycle_body.mod")
        write_obj_file(body_v, body_f, f"{args.output_dir}/cycle_body.obj")
        write_mod_file(front_v, front_f, f"{args.output_dir}/cycle_front.mod")
        write_obj_file(front_v, front_f, f"{args.output_dir}/cycle_front.obj")
        write_mod_file(rear_v, rear_f, f"{args.output_dir}/cycle_rear.mod")
        write_obj_file(rear_v, rear_f, f"{args.output_dir}/cycle_rear.obj")
    
    print("Done!")


if __name__ == '__main__':
    main()

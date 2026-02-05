#!/usr/bin/env python3
"""
Convert standard Wavefront OBJ to Armagetron game format.

Handles:
- Coordinate transformation (Y-up to Z-up, front alignment)
- Triangulation of quads and n-gons
- Scaling
- Output in game's .mod and .obj format
"""

import sys
import argparse
from pathlib import Path


def parse_obj(filename):
    """Parse standard Wavefront OBJ file."""
    vertices = []
    faces = []
    
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            parts = line.split()
            if not parts:
                continue
            
            if parts[0] == 'v' and len(parts) >= 4:
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                vertices.append((x, y, z))
            
            elif parts[0] == 'f':
                # Parse face - handles "f 1 2 3" and "f 1/1/1 2/2/2 3/3/3"
                face_verts = []
                for p in parts[1:]:
                    # Take only vertex index (before any /)
                    v_idx = int(p.split('/')[0])
                    face_verts.append(v_idx)
                if len(face_verts) >= 3:
                    faces.append(face_verts)
    
    return vertices, faces


def transform_coords(vertices, transform='y_up_to_z_up'):
    """
    Transform coordinate system.
    
    Input OBJ (Y-up, -Z forward):
      X = left/right
      Y = up
      Z = back (negative = front)
    
    Game coords:
      X = forward
      Y = left/right  
      Z = up
    """
    transformed = []
    for x, y, z in vertices:
        # Game X = -OBJ_Z (front is positive X)
        # Game Y = OBJ_X (side)
        # Game Z = OBJ_Y (up)
        new_x = -z
        new_y = x
        new_z = y
        transformed.append((new_x, new_y, new_z))
    return transformed


def center_and_scale(vertices, target_length=7.0):
    """Center model and scale to target length."""
    if not vertices:
        return vertices
    
    xs, ys, zs = zip(*vertices)
    
    # Find bounds
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    min_z, max_z = min(zs), max(zs)
    
    # Current dimensions
    length = max_x - min_x  # X is forward
    width = max_y - min_y
    height = max_z - min_z
    
    print(f"  Original bounds: X=[{min_x:.2f}, {max_x:.2f}], Y=[{min_y:.2f}, {max_y:.2f}], Z=[{min_z:.2f}, {max_z:.2f}]")
    print(f"  Dimensions: length={length:.2f}, width={width:.2f}, height={height:.2f}")
    
    # Scale factor based on length
    scale = target_length / length if length > 0 else 1.0
    print(f"  Scale factor: {scale:.3f}")
    
    # Center X and Y, keep Z (height) starting near 0
    center_x = (min_x + max_x) / 2
    center_y = (min_y + max_y) / 2
    
    result = []
    for x, y, z in vertices:
        new_x = (x - center_x) * scale
        new_y = (y - center_y) * scale
        new_z = (z - min_z) * scale  # Shift so bottom is at Z=0
        result.append((new_x, new_y, new_z))
    
    # Print new bounds
    xs, ys, zs = zip(*result)
    print(f"  New bounds: X=[{min(xs):.2f}, {max(xs):.2f}], Y=[{min(ys):.2f}, {max(ys):.2f}], Z=[{min(zs):.2f}, {max(zs):.2f}]")
    
    return result


def triangulate(faces):
    """Convert quads and n-gons to triangles using fan triangulation."""
    triangles = []
    for face in faces:
        if len(face) == 3:
            triangles.append(tuple(face))
        elif len(face) >= 3:
            # Fan triangulation from first vertex
            v0 = face[0]
            for i in range(1, len(face) - 1):
                triangles.append((v0, face[i], face[i + 1]))
    return triangles


def write_mod_file(vertices, faces, filename):
    """Write game's .mod format."""
    with open(filename, 'w') as f:
        for i, (x, y, z) in enumerate(vertices, 1):
            f.write(f"v {i}\t{x:.4f}\t{y:.4f}\t{z:.4f}\n")
        for v1, v2, v3 in faces:
            f.write(f"f \t{v1}\t{v2}\t{v3}\n")


def write_obj_file(vertices, faces, filename):
    """Write game's .obj format."""
    with open(filename, 'w') as f:
        f.write("s 1\n")
        for x, y, z in vertices:
            f.write(f"v {x:.4f}\t{y:.4f}\t{z:.4f}\n")
        for v1, v2, v3 in faces:
            f.write(f"f \t{v1}\t{v2}\t{v3}\n")


def main():
    parser = argparse.ArgumentParser(description='Convert OBJ to Armagetron format')
    parser.add_argument('input', help='Input OBJ file')
    parser.add_argument('--output', '-o', help='Output base name (without extension)')
    parser.add_argument('--scale', '-s', type=float, default=7.0, 
                        help='Target length in game units (default: 7.0)')
    parser.add_argument('--no-transform', action='store_true',
                        help='Skip coordinate transformation')
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if args.output:
        output_base = args.output
    else:
        output_base = input_path.stem + '_game'
    
    print(f"Converting {input_path}...")
    
    # Parse
    vertices, faces = parse_obj(input_path)
    print(f"  Loaded {len(vertices)} vertices, {len(faces)} faces")
    
    # Transform coordinates
    if not args.no_transform:
        print("  Transforming coordinates (Y-up to Z-up)...")
        vertices = transform_coords(vertices)
    
    # Scale and center
    print(f"  Scaling to length {args.scale}...")
    vertices = center_and_scale(vertices, args.scale)
    
    # Triangulate
    orig_face_count = len(faces)
    faces = triangulate(faces)
    print(f"  Triangulated: {orig_face_count} faces -> {len(faces)} triangles")
    
    # Write output
    output_dir = input_path.parent
    mod_path = output_dir / f"{output_base}.mod"
    obj_path = output_dir / f"{output_base}.obj"
    
    write_mod_file(vertices, faces, mod_path)
    write_obj_file(vertices, faces, obj_path)
    
    print(f"\nWritten:")
    print(f"  {mod_path}")
    print(f"  {obj_path}")
    print(f"\nTo use as truck body, copy to cycle_body.mod/obj:")
    print(f"  cp {mod_path} models/cycle_body.mod")
    print(f"  cp {obj_path} models/cycle_body.obj")


if __name__ == '__main__':
    main()

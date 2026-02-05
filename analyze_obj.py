#!/usr/bin/env python3
"""
Analyze OBJ mesh to understand polygon size distribution.
Helps identify small detail geometry that could be removed.
"""

import math
import argparse
from collections import defaultdict


def parse_obj(filename):
    """Parse OBJ file."""
    vertices = []
    faces = []
    
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('v '):
                parts = line.split()
                x, y, z = float(parts[1]), float(parts[2]), float(parts[3])
                vertices.append((x, y, z))
            elif line.startswith('f '):
                parts = line.split()[1:]
                face = [int(p.split('/')[0]) for p in parts]
                faces.append(face)
    
    return vertices, faces


def triangle_area(v1, v2, v3):
    """Calculate area of triangle using cross product."""
    # Vectors from v1 to v2 and v1 to v3
    ax, ay, az = v2[0] - v1[0], v2[1] - v1[1], v2[2] - v1[2]
    bx, by, bz = v3[0] - v1[0], v3[1] - v1[1], v3[2] - v1[2]
    
    # Cross product
    cx = ay * bz - az * by
    cy = az * bx - ax * bz
    cz = ax * by - ay * bx
    
    # Area is half the magnitude
    return 0.5 * math.sqrt(cx*cx + cy*cy + cz*cz)


def face_area(vertices, face):
    """Calculate area of a face (triangulate if needed)."""
    if len(face) < 3:
        return 0
    
    total = 0
    v1 = vertices[face[0] - 1]
    for i in range(1, len(face) - 1):
        v2 = vertices[face[i] - 1]
        v3 = vertices[face[i + 1] - 1]
        total += triangle_area(v1, v2, v3)
    
    return total


def analyze(filename):
    print(f"Parsing {filename}...")
    vertices, faces = parse_obj(filename)
    print(f"  {len(vertices)} vertices, {len(faces)} faces")
    
    # Calculate areas
    print("\nCalculating face areas...")
    areas = []
    face_data = []
    
    for i, face in enumerate(faces):
        area = face_area(vertices, face)
        areas.append(area)
        face_data.append((area, i, face))
    
    # Sort by area
    face_data.sort(key=lambda x: x[0])
    
    # Statistics
    total_area = sum(areas)
    min_area = min(areas)
    max_area = max(areas)
    avg_area = total_area / len(areas)
    
    print(f"\nArea Statistics:")
    print(f"  Total: {total_area:.4f}")
    print(f"  Min:   {min_area:.6f}")
    print(f"  Max:   {max_area:.4f}")
    print(f"  Avg:   {avg_area:.6f}")
    
    # Percentiles
    def percentile(data, p):
        idx = int(len(data) * p / 100)
        return data[idx][0]
    
    print(f"\nPercentiles:")
    for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]:
        print(f"  {p:2d}%: {percentile(face_data, p):.6f}")
    
    # Histogram
    print(f"\nArea Histogram (log scale):")
    
    # Create log-scale buckets
    if min_area > 0:
        log_min = math.floor(math.log10(min_area))
    else:
        log_min = -6
    log_max = math.ceil(math.log10(max_area)) if max_area > 0 else 0
    
    buckets = defaultdict(int)
    bucket_verts = defaultdict(set)
    
    for area, idx, face in face_data:
        if area > 0:
            bucket = math.floor(math.log10(area))
        else:
            bucket = log_min
        buckets[bucket] += 1
        bucket_verts[bucket].update(face)
    
    for b in range(log_min, log_max + 1):
        count = buckets[b]
        vert_count = len(bucket_verts[b])
        bar = '#' * min(50, count // 100)
        print(f"  10^{b:2d}: {count:6d} faces, {vert_count:6d} verts {bar}")
    
    # Cumulative analysis
    print(f"\nCumulative (smallest first):")
    cumulative_verts = set()
    thresholds = [0.001, 0.01, 0.1, 0.5, 1.0]
    
    for thresh in thresholds:
        count = 0
        verts = set()
        for area, idx, face in face_data:
            if area < thresh:
                count += 1
                verts.update(face)
        print(f"  Area < {thresh:5.3f}: {count:6d} faces ({100*count/len(faces):5.1f}%), {len(verts):6d} vertices")
    
    # What if we remove the smallest N% of faces?
    print(f"\nImpact of removing smallest faces:")
    for pct in [10, 25, 50, 75]:
        cutoff_idx = int(len(face_data) * pct / 100)
        removed_faces = cutoff_idx
        
        # Vertices used ONLY by small faces
        small_verts = set()
        large_verts = set()
        for i, (area, idx, face) in enumerate(face_data):
            if i < cutoff_idx:
                small_verts.update(face)
            else:
                large_verts.update(face)
        
        orphan_verts = small_verts - large_verts
        remaining_faces = len(faces) - removed_faces
        remaining_verts = len(vertices) - len(orphan_verts)
        
        print(f"  Remove smallest {pct:2d}%: {remaining_faces:6d} faces, {remaining_verts:6d} verts remain")
    
    return vertices, faces, face_data


def filter_small(filename, output, threshold, min_pct=None):
    """Remove faces smaller than threshold or smallest N%."""
    vertices, faces, face_data = analyze(filename)
    
    if min_pct is not None:
        cutoff_idx = int(len(face_data) * min_pct / 100)
        threshold = face_data[cutoff_idx][0]
        print(f"\nUsing area threshold: {threshold:.6f} (removes smallest {min_pct}%)")
    
    # Keep faces >= threshold
    kept_faces = []
    kept_verts = set()
    
    for area, idx, face in face_data:
        if area >= threshold:
            kept_faces.append(faces[idx])
            kept_verts.update(face)
    
    # Renumber vertices
    sorted_verts = sorted(kept_verts)
    vert_map = {old: new for new, old in enumerate(sorted_verts, 1)}
    
    new_verts = [vertices[v - 1] for v in sorted_verts]
    new_faces = [[vert_map[v] for v in f] for f in kept_faces]
    
    print(f"\nFiltered: {len(new_verts)} verts, {len(new_faces)} faces")
    
    # Write output
    with open(output, 'w') as f:
        f.write("# Filtered OBJ\n")
        for v in new_verts:
            f.write(f"v {v[0]} {v[1]} {v[2]}\n")
        for face in new_faces:
            f.write("f " + " ".join(str(v) for v in face) + "\n")
    
    print(f"Written to {output}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('input', help='Input OBJ file')
    parser.add_argument('--filter', type=float, help='Filter faces smaller than this area')
    parser.add_argument('--remove-pct', type=float, help='Remove smallest N percent of faces')
    parser.add_argument('--output', help='Output filtered OBJ')
    args = parser.parse_args()
    
    if args.filter or args.remove_pct:
        if not args.output:
            args.output = args.input.replace('.obj', '_simplified.obj')
        filter_small(args.input, args.output, args.filter or 0, args.remove_pct)
    else:
        analyze(args.input)


if __name__ == '__main__':
    main()

"""Builds geomsubset_complex_test.usda, a bigger test scene for the GeomSubset selection groups.

Needs a Python with the USD modules (pxr). With the USD from build_usd.bat:
    set PATH=D:\\Build\\MariUsd8\\usd\\lib;D:\\Build\\MariUsd8\\usd\\bin;D:\\Build\\MariUsd8\\oneapi-tbb-2021.13.0\\redist\\intel64\\vc14;%PATH%
    set PYTHONPATH=D:\\Build\\MariUsd8\\usd\\lib\\python
    D:\\Build\\MariUsd8\\python311\\tools\\python.exe make_complex_test.py
"""

import math
from pathlib import Path

from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade, Vt

OUTPUT_FILE = Path(__file__).with_name("geomsubset_complex_test.usda")

SPHERE_RADIUS = 1.5
SPHERE_SEGMENTS = 32
SPHERE_RINGS = 16
CRATE_DIVISIONS = 4

COLORS = {
    "Red": (0.8, 0.1, 0.1),
    "Green": (0.1, 0.7, 0.2),
    "Blue": (0.1, 0.3, 0.8),
    "Yellow": (0.9, 0.8, 0.1),
    "White": (0.85, 0.85, 0.85),
    "Metal": (0.45, 0.47, 0.5),
    "Wood": (0.55, 0.35, 0.15),
}

# Cube sides as (name, corner, u direction, v direction), u x v points outwards
CRATE_SIDES = [
    ("front", (-1, -1, 1), (2, 0, 0), (0, 2, 0)),
    ("back", (1, -1, -1), (-2, 0, 0), (0, 2, 0)),
    ("right", (1, -1, 1), (0, 0, -2), (0, 2, 0)),
    ("left", (-1, -1, -1), (0, 0, 2), (0, 2, 0)),
    ("top", (-1, 1, 1), (2, 0, 0), (0, 0, -2)),
    ("bottom", (-1, -1, -1), (2, 0, 0), (0, 0, 2)),
]

DOCUMENTATION = """Bigger test scene for the GeomSubset selection groups in the Mari USD importer, made by make_complex_test.py.
Expected groups and face counts:

"Create Selection Groups for Material Bindings", one group per bound material:
  Red 36                      BallGeo north_cap 32 + UdimStrip udim_1001 4
  Blue 36                     BallGeo south_cap 32 + UdimStrip udim_1003 4
  White 448                   BallGeo body
  Metal 72                    CrateGeo metal
  Wood 24                     CrateGeo wood
  Green 4                     UdimStrip udim_1002
  Yellow 4                    UdimStrip udim_1004
  unbound_material_subset 4   EdgeGrid, a material binding subset without a material keeps its own name

"Create Selection Groups for Custom Geo Subsets", one group per subset name:
  checker 256, equator_band 64, seam_column 32    BallGeo (512 faces, triangles at the poles)
  side_front / back / right / left / top / bottom 16 each, CrateGeo (a family called "sides")
  trim 24                     CrateGeo 16 + UdimStrip 8
  control 4, whole_mesh 16    EdgeGrid
  animated_indices 2          EdgeGrid faces 8 and 9, the earliest time sample
  negative_and_out_of_range 1 EdgeGrid face 5, with -1, 16 and 999 skipped and a log line
  hidden_only 2               HiddenPanel, only with Include Invisible on
  not created: all_invalid (with a log line), empty, edges_only (edge subset)

Red, Blue and trim only combine across meshes when those meshes land in the same Mari object."""


def build_sphere() -> tuple[list, list[int], list[int], list]:
    """Make a UV sphere with triangles at the poles and quads everywhere else.

    Faces go row by row from the north pole down, SPHERE_SEGMENTS faces per row.
    """
    points = [(0.0, SPHERE_RADIUS, 0.0)]
    for ring in range(1, SPHERE_RINGS):
        theta = math.pi * ring / SPHERE_RINGS
        for segment in range(SPHERE_SEGMENTS):
            phi = 2 * math.pi * segment / SPHERE_SEGMENTS
            points.append((SPHERE_RADIUS * math.sin(theta) * math.cos(phi),
                           SPHERE_RADIUS * math.cos(theta),
                           -SPHERE_RADIUS * math.sin(theta) * math.sin(phi)))
    south_pole = len(points)
    points.append((0.0, -SPHERE_RADIUS, 0.0))

    counts, indices, uvs = [], [], []
    for row in range(SPHERE_RINGS):
        for segment in range(SPHERE_SEGMENTS):
            u0 = segment / SPHERE_SEGMENTS
            u1 = (segment + 1) / SPHERE_SEGMENTS
            v0 = 1 - row / SPHERE_RINGS
            v1 = 1 - (row + 1) / SPHERE_RINGS
            if row == 0:
                counts.append(3)
                indices += [0, _ring_point(1, segment), _ring_point(1, segment + 1)]
                uvs += [((u0 + u1) / 2, v0), (u0, v1), (u1, v1)]
            elif row == SPHERE_RINGS - 1:
                counts.append(3)
                indices += [_ring_point(row, segment), south_pole, _ring_point(row, segment + 1)]
                uvs += [(u0, v0), ((u0 + u1) / 2, v1), (u1, v0)]
            else:
                counts.append(4)
                indices += [_ring_point(row, segment), _ring_point(row + 1, segment),
                            _ring_point(row + 1, segment + 1), _ring_point(row, segment + 1)]
                uvs += [(u0, v0), (u0, v1), (u1, v1), (u1, v0)]
    return points, counts, indices, uvs


def _ring_point(ring: int, segment: int) -> int:
    """Return the point number of a sphere point, wrapping around the seam."""
    return 1 + (ring - 1) * SPHERE_SEGMENTS + segment % SPHERE_SEGMENTS


def build_crate() -> tuple[list, list[int], list[int], list, list[tuple[str, int, int]]]:
    """Make a cube with every side split into a grid of quads, sharing points along the edges.

    Also returns (side name, column, row) for every face so subsets can be picked from it.
    """
    points, counts, indices, uvs, cells = [], [], [], [], []
    point_numbers: dict[tuple, int] = {}
    n = CRATE_DIVISIONS
    for side_number, (name, corner, u_dir, v_dir) in enumerate(CRATE_SIDES):
        # Each side gets its own tile in a 3 x 2 UV layout
        tile_u = 0.025 + (side_number % 3) * 0.325
        tile_v = 0.025 + (side_number // 3) * 0.325
        for row in range(n):
            for column in range(n):
                counts.append(4)
                cells.append((name, column, row))
                for i, j in ((column, row), (column + 1, row), (column + 1, row + 1), (column, row + 1)):
                    position = tuple(round(corner[k] + u_dir[k] * i / n + v_dir[k] * j / n, 6) for k in range(3))
                    if position not in point_numbers:
                        point_numbers[position] = len(points)
                        points.append(position)
                    indices.append(point_numbers[position])
                    uvs.append((tile_u + 0.3 * i / n, tile_v + 0.3 * j / n))
    return points, counts, indices, uvs, cells


def build_grid(columns: int, rows: int, uv_width: float) -> tuple[list, list[int], list[int], list]:
    """Make a flat grid of 1 x 1 quads facing up. Faces are numbered row by row.

    UVs run from 0 to uv_width across and 0 to 1 along, so a width of 4 spreads over four UDIMs.
    """
    points = [(float(i), 0.0, float(-j)) for j in range(rows + 1) for i in range(columns + 1)]
    counts, indices, uvs = [], [], []
    for row in range(rows):
        for column in range(columns):
            counts.append(4)
            for i, j in ((column, row), (column + 1, row), (column + 1, row + 1), (column, row + 1)):
                indices.append(j * (columns + 1) + i)
                uvs.append((uv_width * i / columns, j / rows))
    return points, counts, indices, uvs


def define_mesh(stage: Usd.Stage, path: str, points: list, counts: list[int], indices: list[int],
                uvs: list) -> UsdGeom.Mesh:
    """Create a polygon mesh with a faceVarying st UV set."""
    mesh = UsdGeom.Mesh.Define(stage, path)
    point_array = Vt.Vec3fArray([Gf.Vec3f(*p) for p in points])
    mesh.CreatePointsAttr(point_array)
    mesh.CreateFaceVertexCountsAttr(Vt.IntArray(counts))
    mesh.CreateFaceVertexIndicesAttr(Vt.IntArray(indices))
    mesh.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)
    mesh.CreateExtentAttr(UsdGeom.PointBased.ComputeExtent(point_array))
    st = UsdGeom.PrimvarsAPI(mesh).CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray,
                                                 UsdGeom.Tokens.faceVarying)
    st.Set(Vt.Vec2fArray([Gf.Vec2f(*uv) for uv in uvs]))
    return mesh


def define_xform(stage: Usd.Stage, path: str, translate: tuple, rotate_y: float = 0.0) -> None:
    """Create a group that moves (and optionally turns) everything under it."""
    xform = UsdGeom.Xform.Define(stage, path)
    xform.AddTranslateOp().Set(Gf.Vec3d(*translate))
    if rotate_y:
        xform.AddRotateYOp().Set(rotate_y)


def define_materials(stage: Usd.Stage) -> dict[str, UsdShade.Material]:
    """Create one plain coloured material per entry in COLORS, so subsets show up in a USD viewer."""
    materials = {}
    for name, color in COLORS.items():
        material = UsdShade.Material.Define(stage, f"/World/Looks/{name}")
        shader = UsdShade.Shader.Define(stage, f"/World/Looks/{name}/PreviewSurface")
        shader.CreateIdAttr("UsdPreviewSurface")
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
        shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.6)
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
        materials[name] = material
    return materials


def add_material_subsets(mesh: UsdGeom.Mesh, subsets: dict[str, tuple[list[int], UsdShade.Material]]) -> None:
    """Add materialBind subsets the way DCC exports do: a partition, each with a bound material."""
    binding_api = UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim())
    for name, (faces, material) in subsets.items():
        subset = binding_api.CreateMaterialBindSubset(name, Vt.IntArray(faces), UsdGeom.Tokens.face)
        UsdShade.MaterialBindingAPI.Apply(subset.GetPrim()).Bind(material)
    binding_api.SetMaterialBindSubsetsFamilyType(UsdGeom.Tokens.partition)


def add_subset(mesh: UsdGeom.Mesh, name: str, indices: list[int], element_type: str = "face",
               family_name: str = "") -> UsdGeom.Subset:
    """Add a subset that has nothing to do with materials, optionally as part of a named family."""
    subset = UsdGeom.Subset.Define(mesh.GetPrim().GetStage(), mesh.GetPath().AppendChild(name))
    subset.CreateElementTypeAttr(element_type)
    subset.CreateIndicesAttr(Vt.IntArray(indices))
    if family_name:
        subset.CreateFamilyNameAttr(family_name)
    return subset


def build_ball(stage: Usd.Stage, materials: dict[str, UsdShade.Material]) -> None:
    """Dense sphere mixing triangles and quads, with a material partition and overlapping extra subsets."""
    define_xform(stage, "/World/Props/Ball", (0, SPHERE_RADIUS, 0))
    mesh = define_mesh(stage, "/World/Props/Ball/BallGeo", *build_sphere())

    rows = [list(range(row * SPHERE_SEGMENTS, (row + 1) * SPHERE_SEGMENTS)) for row in range(SPHERE_RINGS)]
    add_material_subsets(mesh, {
        "north_cap": (rows[0], materials["Red"]),
        "body": ([face for row in rows[1:-1] for face in row], materials["White"]),
        "south_cap": (rows[-1], materials["Blue"]),
    })

    half = SPHERE_RINGS // 2
    add_subset(mesh, "checker", [face for r, row in enumerate(rows) for s, face in enumerate(row) if (r + s) % 2 == 0])
    add_subset(mesh, "equator_band", rows[half - 1] + rows[half])
    add_subset(mesh, "seam_column", [face for row in rows for face in (row[0], row[-1])])


def build_crate_prop(stage: Usd.Stage, materials: dict[str, UsdShade.Material]) -> None:
    """Subdivided cube under a moved and turned group, split into metal frame and wood panels."""
    define_xform(stage, "/World/Props/Crate", (4.5, 1, 0), rotate_y=30)
    points, counts, indices, uvs, cells = build_crate()
    mesh = define_mesh(stage, "/World/Props/Crate/CrateGeo", points, counts, indices, uvs)

    last = CRATE_DIVISIONS - 1
    frame = [face for face, (_, c, r) in enumerate(cells) if c in (0, last) or r in (0, last)]
    panels = [face for face, (_, c, r) in enumerate(cells) if 0 < c < last and 0 < r < last]
    add_material_subsets(mesh, {"metal": (frame, materials["Metal"]), "wood": (panels, materials["Wood"])})

    # A named family that isn't materialBind, so these still count as custom subsets
    for side, *_ in CRATE_SIDES:
        add_subset(mesh, f"side_{side}", [face for face, (name, _, _) in enumerate(cells) if name == side],
                   family_name="sides")
    UsdGeom.Subset.SetFamilyType(mesh, "sides", UsdGeom.Tokens.partition)

    # Bottom row of the four upright sides, shares its name with a subset on the UDIM strip
    add_subset(mesh, "trim", [face for face, (name, _, r) in enumerate(cells)
                              if name in ("front", "back", "right", "left") and r == 0])


def build_udim_strip(stage: Usd.Stage, materials: dict[str, UsdShade.Material]) -> None:
    """Strip of quads across UDIMs 1001-1004, with a "trim" subset sharing its name with the crate's."""
    define_xform(stage, "/World/Floor", (-4, 0, 3.5))
    mesh = define_mesh(stage, "/World/Floor/UdimStrip", *build_grid(8, 2, uv_width=4))

    tile_colors = ["Red", "Green", "Blue", "Yellow"]
    add_material_subsets(mesh, {
        f"udim_{1001 + tile}": ([row * 8 + tile * 2 + c for row in range(2) for c in range(2)],
                                materials[tile_colors[tile]])
        for tile in range(4)
    })
    add_subset(mesh, "trim", list(range(8)))


def build_edge_cases(stage: Usd.Stage) -> None:
    """Subsets the importer has to filter or skip, plus an invisible mesh."""
    define_xform(stage, "/World/EdgeCases", (-7, 0, -2))
    mesh = define_mesh(stage, "/World/EdgeCases/EdgeGrid", *build_grid(4, 4, uv_width=1))
    add_subset(mesh, "control", [0, 1, 2, 3])
    add_subset(mesh, "whole_mesh", list(range(16)))
    add_subset(mesh, "negative_and_out_of_range", [-1, 5, 16, 999])
    add_subset(mesh, "all_invalid", [100, 200])
    add_subset(mesh, "empty", [])
    add_subset(mesh, "edges_only", [0, 1], element_type="edge")

    # Material binding subset with no material bound, the group should fall back to the subset name
    UsdShade.MaterialBindingAPI.Apply(mesh.GetPrim()).CreateMaterialBindSubset(
        "unbound_material_subset", Vt.IntArray([12, 13, 14, 15]), UsdGeom.Tokens.face)

    # The importer reads the earliest time sample, so this should come in as faces 8 and 9
    animated = UsdGeom.Subset.Define(stage, mesh.GetPath().AppendChild("animated_indices"))
    animated.CreateElementTypeAttr(UsdGeom.Tokens.face)
    animated_indices = animated.CreateIndicesAttr()
    animated_indices.Set(Vt.IntArray([8, 9]), 1)
    animated_indices.Set(Vt.IntArray([10, 11]), 24)

    hidden = define_mesh(stage, "/World/EdgeCases/HiddenPanel", *build_grid(2, 1, uv_width=1))
    hidden.CreateVisibilityAttr(UsdGeom.Tokens.invisible)
    UsdGeom.XformCommonAPI(hidden).SetTranslate(Gf.Vec3d(0, 0, -5))
    add_subset(hidden, "hidden_only", [0, 1])


def main() -> None:
    """Build the scene and write it out as .usda."""
    stage = Usd.Stage.CreateInMemory()
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
    UsdGeom.SetStageMetersPerUnit(stage, 0.01)
    stage.SetStartTimeCode(1)
    stage.SetEndTimeCode(24)
    stage.GetRootLayer().documentation = DOCUMENTATION

    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())
    UsdGeom.Scope.Define(stage, "/World/Looks")
    materials = define_materials(stage)

    build_ball(stage, materials)
    build_crate_prop(stage, materials)
    build_udim_strip(stage, materials)
    build_edge_cases(stage)

    stage.GetRootLayer().Export(str(OUTPUT_FILE))
    print(f"Wrote {OUTPUT_FILE}")


if __name__ == "__main__":
    main()

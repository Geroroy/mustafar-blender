"""MF 위치 지도 — 질감 없는 재질(요청 표의 번호)을 색으로, 나머지를 회색으로 칠해 게임 카메라로 렌더한다(요청서의 ID_MAP). Blender(bpy).
실행: .venv-bpy/bin/python v0.4_stage/md_fac/mf_idmap.py <MF_STAGE.blend> <textures_spec.csv> <출력 png> [--density 0.3]
"""
import colorsys, csv, json, math, os, sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.dirname(HERE))
import stage_cam as SC  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

BLEND, SPEC, OUT = sys.argv[1:4]
DEN = float(sys.argv[sys.argv.index("--density") + 1]) if "--density" in sys.argv else 0.3
CFG = json.load(open(os.path.join(HERE, "fac_stage_config.json"), encoding="utf-8"))
rows = list(csv.DictReader(open(SPEC, encoding="utf-8-sig")))
want = {r["obj_material"]: int(r["no"]) for r in rows}
bpy.ops.wm.open_mainfile(filepath=BLEND)
D = bpy.data; sc = D.scenes["MO_STAGE"]; cam = D.objects["Game_Output_Iso"]; sc.camera = cam
cols = {}
# the materials with a texture stay as they are (lit, so the map reads); the ones without glow in their number's colour
for ma in D.materials:
    if not ma.use_nodes or ma.name not in want:
        continue
    nt = ma.node_tree; nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission"); out = nt.nodes.new("ShaderNodeOutputMaterial"); nt.links.new(em.outputs[0], out.inputs[0])
    n = want[ma.name]; h = (n * 0.618) % 1.0; r, g, b = colorsys.hsv_to_rgb(h, 0.9, 1.0); cols[n] = (r, g, b)
    em.inputs[0].default_value = (r, g, b, 1); em.inputs[1].default_value = 3.0
SC.setup(sc, cam, CFG, density=DEN)
sc.cycles.samples = 8; sc.cycles.use_denoising = True; sc.view_settings.view_transform = 'Standard'; sc.render.film_transparent = True
sc.render.filepath = OUT + ".raw.png"; bpy.ops.render.render(write_still=True)
im = Image.open(OUT + ".raw.png").convert("RGBA"); bg = Image.new("RGBA", im.size, (90, 90, 96, 255)); bg.alpha_composite(im); im = bg.convert("RGB")
d = ImageDraw.Draw(im); F = ImageFont.truetype("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", 15)
x0, y0 = im.width - 330, 10
d.rectangle((x0 - 6, y0 - 6, im.width - 4, y0 + 20 * len(rows) + 6), fill=(20, 20, 24))
for r in rows:
    n = int(r["no"]); c = tuple(int(v * 255) for v in cols.get(n, (1, 1, 1)))
    d.rectangle((x0, y0 + 2, x0 + 14, y0 + 16), fill=c); d.text((x0 + 20, y0), f'{n} {r["shader"].split("/")[-1]}', font=F, fill=(230, 230, 230)); y0 += 20
d.text((10, 10), "질감 있는 재질은 그대로 · 빛나는 색 = 질감 없는 재질(번호 = textures_spec.csv) · 게임 카메라", font=F, fill=(240, 240, 240))
im.save(OUT, optimize=True); os.remove(OUT + ".raw.png"); print("IDMAP", OUT, im.size)

"""Generate band-sized backgrounds, CGs, sprite layers, title art and icon
from the unpacked 《海蓝之梦》 assets.
"""
import json
import os
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import game_assets as A

SRC = Path(A.SRC)
IMG = Path(A.IMG)
W, H = 336, 480
BG_W = 672
SW, SH = 210, 420


def load_rgba(path):
    with Image.open(path) as im:
        return im.convert("RGBA")


def cover(im, w, h):
    sw, sh = im.size
    scale = max(w / sw, h / sh)
    im = im.resize((max(1, round(sw * scale)), max(1, round(sh * scale))), Image.LANCZOS)
    sw, sh = im.size
    left = (sw - w) // 2
    top = (sh - h) // 2
    return im.crop((left, top, left + w, top + h))


def fit_height(im, h):
    """Scale to h high; keep the original 16:9 width for the CG viewer."""
    w = max(1, round(im.size[0] * h / im.size[1]))
    return im.resize((w, h), Image.LANCZOS)


def used_ops():
    story = Path(ROOT) / "src" / "common" / "story"
    used_bg, used_cg, combos = set(), set(), {}
    for fn in sorted(story.glob("chunk-*.txt")):
        for line in fn.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if parts[0] == "b":
                used_bg.add(parts[1])
            elif parts[0] == "g":
                used_cg.add(parts[1])
            elif parts[0] == "p" and len(parts) >= 7:
                combos.setdefault(parts[1], set()).add(tuple(parts[3:7]))
    return used_bg, used_cg, combos


def save_bg(ident, src, dst):
    if src is None:
        color = (0, 0, 0) if ident == "black" else (255, 255, 255)
        Image.new("RGB", (BG_W, H), color).save(dst, "JPEG", quality=88, optimize=True)
        return
    with Image.open(src) as im:
        im = cover(im.convert("RGB"), BG_W, H)
    im.save(dst, "JPEG", quality=86, optimize=True)


def face_layer(spec, group, value):
    if not value or value == "-":
        return None
    kind = spec["kind"]
    folder = Path(A.ROLE_DIR) / spec["folder"]
    if kind == "xiaox":
        p = folder / ("%s_%s_%s.png" % (spec["tag"], group, value))
    elif kind == "ying":
        if group in ("sweating", "sweat"):
            p = folder / "ying_sweat.png"
        else:
            p = folder / ("ying_%s%s.png" % (group, value))
    elif kind == "xiya":
        p = folder / ("xiya_1_%s_%s.png" % (group, value))
    elif kind in ("deep", "vdeep"):
        p = folder / ("%s_%s_%s.png" % ("deep" if kind == "deep" else "v", group, value))
    else:
        return None
    return p if p.exists() else None


def all_face_paths(spec):
    paths = []
    if spec["kind"] not in ("xiaox", "ying", "xiya", "deep", "vdeep"):
        return paths
    groups = {
        "xiaox": ("eyebrow", "eye", "mouth", "dumb", "blush", "sweating", "cry"),
        "ying": ("eyebrow", "eye", "mouth", "sweat"),
        "xiya": ("eyebrow", "eye", "mouth"),
        "deep": ("eye",),
        "vdeep": ("eye",),
    }[spec["kind"]]
    folder = Path(A.ROLE_DIR) / spec["folder"]
    for p in folder.glob("*.png"):
        low = p.name
        if spec["kind"] == "xiaox" and any(("_" + g) in low for g in groups):
            paths.append(p)
        elif spec["kind"] == "ying" and any(low.startswith("ying_" + g) for g in groups):
            paths.append(p)
        elif spec["kind"] == "xiya" and any(("_" + g + "_") in low for g in groups):
            paths.append(p)
        elif spec["kind"] in ("deep", "vdeep") and ("_eye_" in low):
            paths.append(p)
    return sorted(paths)


def build_sprite(tag, combos):
    spec = A.SPRITES.get(tag)
    if not spec:
        return 0
    folder = Path(A.ROLE_DIR) / spec["folder"]
    body_path = folder / spec["base"]
    if not body_path.exists():
        print("missing body", tag, body_path)
        return 0
    body = load_rgba(body_path)
    bb = body.getbbox() or (0, 0, body.width, body.height)
    fpaths = all_face_paths(spec)
    fb = None
    good_face = []
    for p in fpaths:
        try:
            b = load_rgba(p).getbbox()
        except Exception:
            continue
        # Some special-effect eyes cover almost the whole 2000x3000 canvas.
        # They must not decide the full-body crop (that would shrink the
        # character to a thumbnail); ignore them for geometry.
        if not b:
            continue
        if (b[2] - b[0]) > body.width * 0.8 or (b[3] - b[1]) > body.height * 0.8:
            continue
        good_face.append(p)
        fb = b if fb is None else (min(fb[0], b[0]), min(fb[1], b[1]),
                                   max(fb[2], b[2]), max(fb[3], b[3]))
    fpaths = good_face
    union = bb
    # 3% side padding, 2% top/bottom, like the reference crop.
    px = int((union[2] - union[0]) * 0.04)
    py = int((union[3] - union[1]) * 0.03)
    x0 = max(0, union[0] - px)
    x1 = min(body.width, union[2] + px)
    y0 = max(0, union[1] - py)
    y1 = min(body.height, union[3] + py)

    bw, bh = x1 - x0, y1 - y0
    scale = min((SW - 8) / bw, (SH - 8) / bh)
    full = spec["kind"] in ("xiaox", "ying", "xiya")
    nw, nh = max(1, round(bw * scale)), max(1, round(bh * scale))
    ox = (SW - nw) // 2
    oy = (SH - nh) if full else (SH - nh) // 2

    out = IMG / "s" / tag
    out.mkdir(parents=True, exist_ok=True)
    base = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
    base.alpha_composite(body.crop((x0, y0, x1, y1)).resize((nw, nh), Image.LANCZOS), (ox, oy))
    base.save(out / "base.png", "PNG", optimize=True)

    meta = {"face": [0, 0, 0, 0], "size": [SW, SH]}
    if fb:
        fx0 = max(0, round(ox + (fb[0] - x0) * scale) - 2)
        fy0 = max(0, round(oy + (fb[1] - y0) * scale) - 2)
        fx1 = min(SW, round(ox + (fb[2] - x0) * scale) + 2)
        fy1 = min(SH, round(oy + (fb[3] - y0) * scale) + 2)
        meta["face"] = [fx0, fy0, fx1, fy1]
        fw, fh = fx1 - fx0, fy1 - fy0

        # Prepare each face layer once, at final face-box size.
        small = {}
        for p in fpaths:
            im = load_rgba(p).crop(fb).resize((fw, fh), Image.LANCZOS)
            small[p.name] = im

        made = 0
        for eye, brow, mouth, extra in sorted(combos):
            canvas = Image.new("RGBA", (fw, fh), (0, 0, 0, 0))
            for group, value in (("eyebrow", brow), ("eye", eye), ("mouth", mouth)):
                p = face_layer(spec, group, value)
                if p and p.name in small:
                    canvas = Image.alpha_composite(canvas, small[p.name])
            for e in (extra or "").split(","):
                e = e.strip()
                if not e:
                    continue
                group = e.split("_")[0] if e.startswith("dumb_") else e
                p = face_layer(spec, group, e.replace("dumb_", "") if group == "dumb" else e)
                if p and p.name in small:
                    canvas = Image.alpha_composite(canvas, small[p.name])
            if canvas.getbbox() is None:
                continue
            name = A.face_file(eye, brow, mouth, [x for x in (extra or "").split(",") if x])
            canvas.save(out / name, "PNG", optimize=True)
            made += 1
        if not made and not combos:
            # Body-only characters still need a base; no face file is fine.
            pass

    with open(out / "meta.json", "w", encoding="utf-8") as fh:
        json.dump(meta, fh)
    return len(list(out.glob("face__*.png")))


def build_ui(used_bg):
    ui = IMG / "ui"
    ui.mkdir(parents=True, exist_ok=True)

    # Original 1920x1080 main menu = game_menu.png (Xiaox art) with
    # main_menu.png (alpha gradient + title logo) composited on top. Keep the
    # complete 16:9 frame as a 336x189 banner; the menu sheet starts below it.
    gui = SRC / "05_其他素材" / "images" / "gui"
    game_src = gui / "game_menu.png"
    menu_src = gui / "main_menu.png"
    if game_src.exists():
        art = Image.open(game_src).convert("RGBA")
        if menu_src.exists():
            over = Image.open(menu_src).convert("RGBA")
            art = Image.alpha_composite(art, over)
        title = art.convert("RGB").resize((W, W * 9 // 16), Image.LANCZOS)
    else:
        title = Image.new("RGB", (W, W * 9 // 16), (79, 194, 220))
    title.save(ui / "title_bg.png", "PNG", optimize=True)

    # reading board: vertical gradient, clear at the top
    board = Image.new("RGBA", (W, 180), (0, 0, 0, 0))
    bpx = board.load()
    for y in range(180):
        a = int(8 + 172 * (y / 30.0)) if y < 30 else min(232, int(180 + 52 * ((y - 30) / 40.0)))
        for x in range(W):
            bpx[x, y] = (14, 16, 24, min(232, a))
    board.save(ui / "board.png", "PNG", optimize=True)

    head = Image.new("RGBA", (W, 72), (0, 0, 0, 0))
    hpx = head.load()
    for y in range(72):
        a = 232 if y < 52 else int(232 * (1 - (y - 52) / 20.0))
        for x in range(W):
            hpx[x, y] = (26, 28, 36, a)
    ImageDraw.Draw(head).line((0, 71, W, 71), fill=(255, 255, 255, 46), width=1)
    head.save(ui / "headbar.png", "PNG", optimize=True)

    foot = Image.new("RGBA", (W, 56), (0, 0, 0, 0))
    fpx = foot.load()
    for y in range(56):
        a = int(120 * (y / 55.0) ** 1.5)
        for x in range(W):
            fpx[x, y] = (14, 16, 22, a)
    foot.save(ui / "footbar.png", "PNG", optimize=True)

    lock = Image.new("RGB", (96, 54), (32, 26, 40))
    d = ImageDraw.Draw(lock)
    try:
        f = ImageFont.load_default(size=28)
    except TypeError:
        f = ImageFont.load_default()
    d.text((40, 12), "?", fill=(120, 104, 128), font=f)
    lock.save(ui / "locked.png", "PNG", optimize=True)

    # App icon: the game's own window_icon.png (250x250).
    icon_src = SRC / "05_其他素材" / "images" / "gui" / "window_icon.png"
    if icon_src.exists():
        with Image.open(icon_src) as im:
            icon = im.convert("RGBA").resize((192, 192), Image.LANCZOS)
    else:
        icon = Image.new("RGBA", (192, 192), (79, 194, 220, 255))
    # Vela shows the icon as a square bitmap; round the corners ourselves so
    # the app-list tile does not look like a hard-edged photo.
    scale = 4
    mask = Image.new("L", (192 * scale, 192 * scale), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, 192 * scale - 1, 192 * scale - 1), radius=42 * scale, fill=255
    )
    mask = mask.resize((192, 192), Image.LANCZOS)
    icon.putalpha(ImageChops.multiply(icon.getchannel("A"), mask))
    icon.save(Path(ROOT) / "src" / "common" / "icon.png", "PNG", optimize=True)


def write_assets(bgs, cgs):
    sprites = {}
    for tag in sorted(os.listdir(IMG / "s")):
        d = IMG / "s" / tag
        sprites[tag] = sorted(f for f in os.listdir(d) if f.endswith(".png"))
        meta = d / "meta.json"
        if meta.exists():
            sprites[tag + "__meta"] = json.load(open(meta, encoding="utf-8"))
    wide = {}
    for f in sorted(os.listdir(IMG / "w")):
        if f.endswith(".png"):
            with Image.open(IMG / "w" / f) as im:
                wide[f[:-4]] = im.size[0]
    out = Path(ROOT) / "src" / "common" / "assets.js"
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("/* generated by tools/build_assets.py — do not edit */\n")
        fh.write("export const BG = %s;\n" % json.dumps(bgs, ensure_ascii=False))
        fh.write("export const CG = %s;\n" % json.dumps(cgs, ensure_ascii=False))
        fh.write("export const SPRITES = %s;\n" % json.dumps(sprites, ensure_ascii=False))
        fh.write("export const CG_WIDE = %s;\n" % json.dumps(wide, ensure_ascii=False))
        fh.write("""
export function bgPath(id) { return '/common/img/b/' + id + '.jpg' }
export function cgPath(id) { return '/common/img/w/' + id + '.png' }
export function cgThumb(id) { return '/common/img/t/' + id + '.png' }
export function cgWide(id) { return '/common/img/w/' + id + '.png' }
export function spritePath(tag, file) { return '/common/img/s/' + tag + '/' + file }
export function hasSprite(tag, file) {
  return !!(SPRITES[tag] && SPRITES[tag].indexOf(file) >= 0)
}
""")


def main():
    used_bg, used_cg, combos = used_ops()
    used_bg.update(("black", "white"))
    print("used bg", len(used_bg), "cg", len(used_cg), "sprite tags", len(combos))
    for sub in ("b", "s", "t", "w"):
        shutil.rmtree(IMG / sub, ignore_errors=True)
        (IMG / sub).mkdir(parents=True, exist_ok=True)

    for ident in sorted(used_bg):
        src = A.BG.get(ident)
        if src is None and ident not in ("black", "white"):
            continue
        save_bg(ident, src, IMG / "b" / (ident + ".jpg"))

    for ident in sorted(A.CG):
        if ident not in used_cg and ident not in used_cg:
            # still build the gallery (the story may not reach every CG)
            pass
        src = A.CG[ident]
        if not Path(src).exists():
            print("missing cg", ident, src)
            continue
        with Image.open(src) as im:
            wide = fit_height(im.convert("RGB"), H)
            wide.quantize(colors=160, method=Image.MEDIANCUT, dither=Image.FLOYDSTEINBERG).save(
                IMG / "w" / (ident + ".png"), "PNG", optimize=True
            )
            thumb = cover(im.convert("RGB"), 96, 54)
            thumb.quantize(colors=96).save(IMG / "t" / (ident + ".png"), "PNG", optimize=True)

    total_faces = 0
    for tag in sorted(combos):
        total_faces += build_sprite(tag, combos[tag])
    print("face files", total_faces)

    build_ui(used_bg)
    write_assets(sorted(used_bg), sorted(A.CG))

    total = 0
    for dp, _, fs in os.walk(IMG):
        for f in fs:
            total += os.path.getsize(os.path.join(dp, f))
    print("images: %.2f MB" % (total / 1048576))


if __name__ == "__main__":
    main()

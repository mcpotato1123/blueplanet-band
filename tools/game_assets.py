"""Shared asset map for the Vela port.

Game source is the already-unpacked PC build:
  ../unpacked/02_背景, 03_CG, 01_立绘/分层素材
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT.parent / "unpacked"
BG_DIR = SRC / "02_背景"
CG_DIR = SRC / "03_CG"
ROLE_DIR = SRC / "01_立绘" / "分层素材"
IMG = ROOT / "src" / "common" / "img"

# Background id -> source PNG. DLC backgrounds get a "DLC_" prefix.
BG = {}
for p in sorted(BG_DIR.rglob("*.png")):
    ident = ("DLC_" if p.parent.name == "DLC背景" else "") + p.stem
    BG[ident] = p
BG["black"] = None
BG["white"] = None

# A compact gallery: one representative image per CG scene. Keeping the set
# small matters on the band; the story silently skips CGs that are not here.
CG = {
    "DLC_QCG_1": CG_DIR / "DLC_CG" / "QCG_1.png",
    "DLC_QCG_2": CG_DIR / "DLC_CG" / "QCG_2.png",
    "DLC_QCG_3": CG_DIR / "DLC_CG" / "QCG_3.png",
    "DLC_QCG_4": CG_DIR / "DLC_CG" / "QCG_4.png",
    "DLC_QCG_5": CG_DIR / "DLC_CG" / "QCG_5.png",
    "DLC_Draw_1": CG_DIR / "DLC_CG" / "Draw_1.png",
    "DLC_xiaox_married": CG_DIR / "DLC_CG" / "xiaox_married.png",
    "CG_xiaox_kiss": CG_DIR / "主线CG" / "xiaox_kiss" / "CG_xiaox_kiss.png",
    "CG_xiaox_sleep_open": CG_DIR / "主线CG" / "xiaox_sleep" / "open_smile.png",
    "CG_xiaox_sleep_close": CG_DIR / "主线CG" / "xiaox_sleep" / "close_smile.png",
    "CG_xiaox_shooting": CG_DIR / "主线CG" / "xiaox_shooting" / "shooting_1.png",
    "CG_xiaox_memory": CG_DIR / "主线CG" / "xiaox_memory" / "3.png",
    "CG_xiaox_Rooftop": CG_DIR / "主线CG" / "xiaox_Rooftop" / "a_mouth1.png",
    "CG_xiaox_Q_food": CG_DIR / "主线CG" / "xiaox_Q" / "food_wait.png",
    "CG_xiaox_Q_draw": CG_DIR / "主线CG" / "xiaox_Q2" / "1.png",
    "CG_xiaox_gameplayer": CG_DIR / "主线CG" / "xiaox_gameplayer" / "小希游戏_调色_0000.png",
    "CG_xiaox_Q3": CG_DIR / "主线CG" / "xiaox_Q3" / "1.png",
}


def background(name):
    if not name:
        return None
    if name.lower() == "dusk":
        name = "Dusk"
    if name in BG:
        return name
    return None


def cg(name):
    if not name:
        return None
    if name in CG:
        return name
    if name.startswith("CG_xiaox_sleep_close"):
        return "CG_xiaox_sleep_close"
    if name.startswith("CG_xiaox_sleep_open"):
        return "CG_xiaox_sleep_open"
    if name.startswith("CG_xiaox_sleep"):
        return "CG_xiaox_sleep_open"
    if name.startswith("CG_xiaox_shooting"):
        return "CG_xiaox_shooting"
    if name.startswith("CG_xiaox_memory"):
        return "CG_xiaox_memory"
    if name.startswith("CG_xiaox_Rooftop"):
        return "CG_xiaox_Rooftop"
    if name.startswith("CG_xiaox_gameplayer"):
        return "CG_xiaox_gameplayer"
    if name.startswith("CG_xiaox_kiss"):
        return "CG_xiaox_kiss"
    if name.startswith("CG_xiaox_Q_food") or name.startswith("CG_xiaox_Q_"):
        return "CG_xiaox_Q_food"
    if name.startswith("CG_xiaox_Q_draw") or name.startswith("CG_xiaox_Q2") or name.startswith("CG_xiaox_Q3") or name.startswith("CG_xiaox_Q4"):
        return "CG_xiaox_Q_draw"
    if name.startswith("CG_xiaox_Q"):
        return "CG_xiaox_Q_draw"
    if name.startswith("QCG_"):
        return "DLC_" + name
    return None


# tag -> (role folder, base file, kind, body number)
# kind: xiaox / ying / xiya / deep / vdeep / adeep / err / tx / bodyonly
SPRITES = {}


def _add(tag, folder, base, kind, body=""):
    SPRITES[tag] = {
        "tag": tag,
        "folder": folder,
        "base": base,
        "kind": kind,
        "body": body,
    }


_add("xiaox_1", "xiaox_1", "xiaox_1_body.png", "xiaox", "1")
_add("xiaox_2", "xiaox_2", "xiaox_2_body.png", "xiaox", "2")
_add("xiaox_3", "xiaox_3", "xiaox_3_body.png", "bodyonly", "3")
_add("xiaox_4", "xiaox_4", "xiaox_4_body.png", "bodyonly", "4")
_add("ying_1", "ying_figure", "ying_body.png", "ying", "1")
_add("ying_2", "ying_figure", "ying_body2.png", "ying", "2")
_add("ying_3", "ying_figure", "ying_body3.png", "bodyonly", "3")
_add("xiya_1", "xiya_1", "xiya_1_body.png", "xiya", "1")
_add("v_deep", "v_deep", "v_body.png", "vdeep", "")
_add("a_deep", "a_deep", "a_body.png", "bodyonly", "")
for _n in range(1, 6):
    _add("deep_%d" % _n, "deepsleep", "deep_body_%d.png" % _n, "deep", str(_n))
for _n in range(2, 6):
    _add("err_deep_%d" % _n, "err_deep", "gpp_body_%d.png" % _n, "bodyonly", str(_n))
for _n in range(1, 8):
    _add("tx_head_%d" % _n, "tx", "tx_head_%d.png" % _n, "tx", str(_n))


def sprite_tag(name):
    """Ren'Py image name tuple -> our sprite tag, or None."""
    if not name:
        return None
    head = name[0]
    if head == "xiaox":
        body = next((a for a in name[1:] if a in ("1", "2", "3", "4")), "1")
        return "xiaox_" + body
    if head == "ying":
        body = next((a for a in name[1:] if a in ("1", "2", "3")), "1")
        return "ying_" + body
    if head == "xiya":
        return "xiya_1"
    if head == "deep":
        body = next((a for a in name[1:] if a.startswith("body_")), None)
        if body:
            return "deep_" + body.split("_")[1]
        return "deep_1"
    if head == "v_deep":
        return "v_deep"
    if head == "a_deep":
        return "a_deep"
    if head == "err_deep":
        body = next((a for a in name[1:] if a.startswith("body_")), None)
        return "err_deep_" + (body.split("_")[1] if body else "2")
    if head == "tx_head":
        state = next((a for a in name[1:] if a.startswith("state")), "state1")
        n = state.replace("state_ds_", "").replace("state_vds_", "").replace("state", "")
        return "tx_head_" + n
    return None


def sprite_attrs(name):
    """Extract (eye, brow, mouth, extra) from a Ren'Py image name."""
    eye = brow = mouth = "-"
    extra = []
    for a in name[1:]:
        if a.startswith("eye_"):
            eye = a[4:]
        elif a.startswith("eyebrow_"):
            brow = a[8:]
        elif a.startswith("mouth_"):
            mouth = a[6:]
        elif a.startswith("dumb_"):
            extra.append(a)
        elif a in ("blush", "sweating", "cry"):
            extra.append(a)
    return eye, brow, mouth, extra


def face_file(eye, brow, mouth, extra):
    e = "_".join(extra) if extra else "-"
    return "face__%s__%s__%s__%s.png" % (eye or "-", brow or "-", mouth or "-", e)

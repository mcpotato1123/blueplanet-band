"""Compile the unpacked Ren'Py AST of 《海蓝星之梦》 into the band's
tab-separated instruction stream.

The engine is the same instruction set used by the reference project:
  s who text / b bg / p tag pos eye brow mouth extra / h tag / g cg
  m choice<US>target ... / j index / e / n name / d date / c chapter
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "tools"))

import game_assets as assets
import rpyc_ast

ROOT = os.path.dirname(HERE)
SRC = os.path.join(os.path.dirname(ROOT), "unpacked")
STORY = os.path.join(ROOT, "src", "common", "story")
SCRIPT_ROOT = os.path.join(SRC, "extracted", "msvcp140")
DLC_SCRIPT = os.path.join(SRC, "extracted", "DLC", "DLC", "DLC.rpyc")

US = "\x1f"
CHUNK = 128
TAG = re.compile(r"\{[^{}]*\}")


def clean_text(s):
    if not isinstance(s, str):
        return ""
    s = s.replace("%%", "%")
    s = s.replace("\\n", "\n")
    s = TAG.sub("", s)
    s = s.replace("[[", "[")
    s = s.replace("\t", " ")
    s = s.replace("\n", "\\n")
    return s.strip()


WHO = {
    "me": "我",
    "wm": "无名",
    "xiaox": "小希",
    "xi": "希",
    "ying": "影",
    "xiya": "希娅",
    "b": "DeepSleep",
    "v_deep": "五号",
    "a_deep": "阿尔法",
    "err_deep": "变异机器人",
    "evirus": "EVIRUS",
    "ch": "辰火",
    "jz": "记者",
    "jjr": "对面的经纪人",
    "txa": "同学A",
    "txb": "同学B",
    "txc": "同学C",
    "ls": "老师",
    "ldy": "老大爷",
    "ds": "电视",
    "unknown": "？？？",
    "npc": "NPC",
    "npc2": "NPC2",
    "diary": "日记",
    "x": "",
    "narrator": "",
    "nvl_narrator_outline": "",
    "NVL": "",
    "xsp_nvl": "",
    "None": "",
    "": "",
}

NAME_SET = {v for v in WHO.values() if v}

def split_inline_speaker(speaker, text):
    """Some authored lines are narrator nodes whose text starts with a
    character name, e.g. "影：『...』".  Pull that prefix into the speaker
    slot so the reader does not render "旁白：影：..." (or a doubled name).
    """
    if "：" not in text:
        return speaker, text
    head, rest = text.split("：", 1)
    head = head.strip()
    if head in NAME_SET and (not speaker or speaker == head):
        return head, rest.strip()
    return speaker, text

FILES = [
    ("ep1", "EP.1 序章", os.path.join(SCRIPT_ROOT, "main", "ep1.rpyc")),
    ("ep2", "EP.2", os.path.join(SCRIPT_ROOT, "main", "ep2.rpyc")),
    ("ep3", "EP.3", os.path.join(SCRIPT_ROOT, "main", "ep3.rpyc")),
    ("ep4", "EP.4", os.path.join(SCRIPT_ROOT, "main", "ep4.rpyc")),
    ("ep5", "EP.5", os.path.join(SCRIPT_ROOT, "main", "ep5.rpyc")),
    ("ep6", "EP.6", os.path.join(SCRIPT_ROOT, "main", "ep6.rpyc")),
    ("ep7", "EP.7", os.path.join(SCRIPT_ROOT, "main", "ep7.rpyc")),
    ("ep8", "EP.8", os.path.join(SCRIPT_ROOT, "main", "ep8.rpyc")),
    ("ep9", "EP.9", os.path.join(SCRIPT_ROOT, "main", "ep9.rpyc")),
    ("ep10", "EP.10", os.path.join(SCRIPT_ROOT, "main", "ep10.rpyc")),
    ("ep11", "EP.11", os.path.join(SCRIPT_ROOT, "main", "ep11.rpyc")),
    ("ne", "NE 线", os.path.join(SCRIPT_ROOT, "main", "ne.rpyc")),
    ("dlc", "DLC 番外", DLC_SCRIPT),
]


def char_key(tag):
    if tag.startswith("xiaox_"):
        return "xiaox"
    if tag.startswith("ying_"):
        return "ying"
    if tag.startswith("xiya_"):
        return "xiya"
    if tag.startswith("deep_"):
        return "deep"
    if tag.startswith("err_deep_"):
        return "err_deep"
    if tag.startswith("tx_head_"):
        return "tx_head"
    if tag == "v_deep":
        return "v_deep"
    if tag == "a_deep":
        return "a_deep"
    return tag


def at_pos(node):
    ims = getattr(node, "imspec", None)
    if not ims or len(ims) < 4:
        return "c"
    parts = []
    for x in ims[3] or []:
        src = rpyc_ast.expr_source(x)
        if src:
            parts.append(src.lower())
    text = " ".join(parts)
    if not text:
        return "c"
    if "left" in text or "a1" in text or text in ("l", "cl", "fl"):
        return "l"
    if "right" in text or "a3" in text or text in ("r", "cr", "rr"):
        return "r"
    return "c"


class Compiler:
    def __init__(self):
        self.ops = []
        self.labels = {}
        self.pending = []
        self.chapters = []
        self.active = {}       # key -> tag
        self.last_speaker = ""
        self.warnings = []

    def emit(self, *fields):
        self.ops.append([str(x) for x in fields])
        return len(self.ops) - 1

    def hide_all(self):
        for tag in list(self.active.values()):
            self.emit("h", tag)
        self.active = {}

    def hide_key(self, key):
        tag = self.active.get(key)
        if tag:
            self.emit("h", tag)
            del self.active[key]

    def compile_file(self, key, title, path):
        start = len(self.ops)
        data, stmts = rpyc_ast.load(path)
        self.chapters.append({"id": key, "title": title, "start": start})
        self.compile_block(stmts)
        # A chapter started manually must not fall through to the next chapter
        # if its script forgot an explicit jump/return.
        self.emit("e")
        return start

    def compile_block(self, block):
        for n in block or []:
            self.compile_node(n)

    def compile_node(self, n):
        t = type(n).__name__
        if t == "Label":
            self.labels[getattr(n, "_name", "")] = len(self.ops)
            self.compile_block(getattr(n, "block", None))

        elif t == "Say":
            if getattr(n, "what", None) is None:
                return
            who = getattr(n, "who", None)
            who_s = str(who) if who is not None else "None"
            if who_s == "extend":
                speaker = self.last_speaker
            else:
                speaker = WHO.get(who_s, who_s)
                self.last_speaker = speaker
            text = clean_text(getattr(n, "what", ""))
            speaker, text = split_inline_speaker(speaker, text)
            if text:
                self.emit("s", speaker, text)

        elif t == "Scene":
            ims = getattr(n, "imspec", None)
            name = ims[0][0] if ims and ims[0] else ""
            bg = assets.background(name)
            cg = assets.cg(name)
            self.hide_all()
            self.emit("h", "@fg")
            if cg:
                self.emit("g", cg)
            elif bg:
                self.emit("b", bg)
            elif name.lower() in ("black", "white"):
                self.emit("b", name.lower())

        elif t == "Show":
            ims = getattr(n, "imspec", None)
            if not ims or not ims[0]:
                return
            name = ims[0]
            tag = assets.sprite_tag(name)
            if tag and tag in assets.SPRITES:
                key = char_key(tag)
                old = self.active.get(key)
                if old and old != tag:
                    self.emit("h", old)
                eye, brow, mouth, extra = assets.sprite_attrs(name)
                pos = at_pos(n)
                self.emit("p", tag, pos, eye, brow, mouth, ",".join(sorted(extra)))
                self.active[key] = tag
                return
            full = name[0]
            bg = assets.background(full)
            cg = assets.cg(full)
            if cg:
                self.emit("g", cg)
            elif bg:
                self.emit("b", bg)

        elif t == "Hide":
            ims = getattr(n, "imspec", None)
            tag = ims[0][0] if ims and ims[0] else ""
            key = char_key(tag)
            if key in self.active:
                self.hide_key(key)
            else:
                self.emit("h", "@fg")

        elif t == "Menu":
            self.compile_menu(n)

        elif t == "Jump":
            idx = self.emit("j", "")
            self.pending.append((idx, getattr(n, "target", "")))

        elif t == "Call":
            # achievement / screen calls have no bearing on the story stream
            return

        elif t == "If":
            self.compile_if(n)

        elif t == "Return":
            self.emit("e")

        # Init / Image / Define / Python / With / Camera / UserStatement are
        # metadata or local effects; the band only needs text and stage state.

    def compile_menu(self, n):
        items = getattr(n, "items", None) or []
        items = [i for i in items if i and i[0] and clean_text(i[0]) != "..."]
        if not items:
            return
        menu_idx = self.emit("m", "")
        spec = []
        ends = []
        for caption, _cond, block in items:
            target = len(self.ops)
            spec.extend([clean_text(caption), str(target)])
            self.compile_block(block)
            j = self.emit("j", "")
            ends.append(j)
        after = len(self.ops)
        self.ops[menu_idx][1] = US.join(spec)
        for j in ends:
            self.ops[j][1] = str(after)

    def compile_if(self, n):
        entries = getattr(n, "entries", None) or []
        if not entries:
            return
        conditions = [rpyc_ast.expr_source(c).strip() for c, _ in entries]
        if any(c.startswith("TEST_") for c in conditions):
            return
        # The band build deliberately linearises rare conditional branches.
        # For the ending fork, choose the true-ending branch.
        if any("ep9_choice" in c for c in conditions):
            block = entries[-1][1]
        elif len(entries) == 1:
            block = entries[0][1]
        else:
            block = entries[-1][1]
        kinds = {type(x).__name__ for x in (block or [])}
        if kinds and kinds <= {"Python", "UserStatement"}:
            return
        self.compile_block(block)

    def finish(self):
        # Close the last chapter and resolve label references.
        self.emit("e")
        for idx, label in self.pending:
            if label in self.labels:
                self.ops[idx][1] = str(self.labels[label])
            else:
                self.warnings.append("unresolved label: %s" % label)
                self.ops[idx][1] = str(len(self.ops) - 1)


def main():
    comp = Compiler()
    for key, title, path in FILES:
        if not os.path.exists(path):
            raise SystemExit("missing script: " + path)
        comp.compile_file(key, title, path)
    comp.finish()

    os.makedirs(STORY, exist_ok=True)
    for fn in os.listdir(STORY):
        if fn.startswith("chunk-") or fn in ("index.txt", "index.json"):
            os.remove(os.path.join(STORY, fn))

    lines = ["\t".join(op) for op in comp.ops]
    chunks = []
    for start in range(0, len(lines), CHUNK):
        part = lines[start:start + CHUNK]
        fn = "chunk-%03d.txt" % (start // CHUNK)
        with open(os.path.join(STORY, fn), "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(part) + "\n")
        chunks.append({"file": "/common/story/" + fn, "start": start, "count": len(part)})

    index = {
        "version": 1,
        "total": len(lines),
        "chunks": chunks,
        "chapters": comp.chapters,
    }
    with open(os.path.join(STORY, "index.txt"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(index, fh, ensure_ascii=False, separators=(",", ":"))

    kinds = {}
    for op in comp.ops:
        kinds[op[0]] = kinds.get(op[0], 0) + 1
    print("ops", len(lines), kinds)
    print("chunks", len(chunks), "chapters", len(comp.chapters))
    for w in comp.warnings:
        print("WARN", w)


if __name__ == "__main__":
    main()

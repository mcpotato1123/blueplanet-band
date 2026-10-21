import pickle
import struct
import zlib
from pathlib import Path


class Node:
    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._args = args
        return obj

    def __setstate__(self, state):
        if isinstance(state, dict):
            self.__dict__.update(state)
        elif isinstance(state, tuple) and len(state) == 2:
            d, slots = state
            if isinstance(d, dict):
                self.__dict__.update(d)
            if isinstance(slots, dict):
                self.__dict__.update(slots)
        else:
            self._state = state

    def __repr__(self):
        return "<%s.%s>" % (type(self).__module__, type(self).__name__)


class Sentinel:
    def __init__(self, name):
        self.name = name


_cls = {}


def _node_class(module, name):
    key = (module, name)
    if key not in _cls:
        _cls[key] = type(name, (Node,), {"__module__": module})
    return _cls[key]


class Unpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module == "renpy.object" and name == "Sentinel":
            return Sentinel
        if module == "renpy.revertable":
            import collections
            return {
                "RevertableDict": dict,
                "RevertableList": list,
                "RevertableSet": set,
                "RevertableDefaultDict": collections.defaultdict,
            }.get(name, _node_class(module, name))
        if module.startswith("renpy."):
            return _node_class(module, name)
        if module in ("builtins", "collections", "copyreg", "codecs", "_codecs", "types"):
            return super().find_class(module, name)
        return _node_class(module, name)


def load(path):
    raw = Path(path).read_bytes()
    if raw.startswith(b"RENPY RPC2"):
        pos = 10
        slots = []
        while True:
            t = struct.unpack_from("<I", raw, pos)[0]
            if t == 0:
                break
            st, ln = struct.unpack_from("<II", raw, pos + 4)
            slots.append((t, st, ln))
            pos += 12
        st, ln = next((st, ln) for t, st, ln in slots if t == 1)
        raw = zlib.decompress(raw[st:st + ln])
    import io
    return Unpickler(io.BytesIO(raw)).load()


def walk(nodes):
    for n in nodes:
        yield n
        b = getattr(n, "block", None)
        if isinstance(b, list):
            yield from walk(b)
        if type(n).__name__ == "Menu":
            for _label, _cond, block in n.items:
                if isinstance(block, list):
                    yield from walk(block)
        if type(n).__name__ == "If":
            for _cond, block in n.entries:
                if isinstance(block, list):
                    yield from walk(block)


def expr_source(obj):
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    args = getattr(obj, "_args", None)
    if args:
        return args[0] if isinstance(args[0], str) else str(args[0])
    return ""

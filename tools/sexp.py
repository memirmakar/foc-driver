"""Minimal S-expression parser / serializer for KiCad files."""
import re

_tok = re.compile(r'\s*(?:(\()|(\))|("(?:[^"\\]|\\.)*")|([^\s()"]+))')


class Sym(str):
    """Bare (unquoted) atom."""


def parse(text):
    pos = 0
    stack = [[]]
    n = len(text)
    while pos < n:
        m = _tok.match(text, pos)
        if not m:
            if text[pos:].strip() == "":
                break
            raise ValueError("parse error at %d" % pos)
        pos = m.end()
        if m.group(1):
            stack.append([])
        elif m.group(2):
            e = stack.pop()
            stack[-1].append(e)
        elif m.group(3) is not None:
            s = m.group(3)[1:-1]
            s = s.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
            stack[-1].append(s)
        else:
            stack[-1].append(Sym(m.group(4)))
    return stack[0][0]


def _atom(a):
    if isinstance(a, Sym):
        return str(a)
    if isinstance(a, bool):
        return "yes" if a else "no"
    if isinstance(a, (int,)):
        return str(a)
    if isinstance(a, float):
        s = ("%.4f" % a).rstrip("0").rstrip(".")
        return "0" if s in ("-0", "") else s
    s = str(a).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return '"%s"' % s


def dumps(e, ind=0):
    if not isinstance(e, list):
        return _atom(e)
    if not e:
        return "()"
    simple = all(not isinstance(x, list) for x in e)
    if simple:
        return "(" + " ".join(_atom(x) for x in e) + ")"
    out = "(" + " ".join(_atom(x) for x in e if not isinstance(x, list))
    # keep head atoms, then children each on new line
    parts = []
    for x in e:
        if isinstance(x, list):
            parts.append("\n" + "\t" * (ind + 1) + dumps(x, ind + 1))
    # atoms after lists (rare) are not supported in order; KiCad files don't need it
    return out + "".join(parts) + "\n" + "\t" * ind + ")"


def find(e, key):
    for x in e:
        if isinstance(x, list) and x and x[0] == key:
            return x
    return None


def findall(e, key):
    return [x for x in e if isinstance(x, list) and x and x[0] == key]

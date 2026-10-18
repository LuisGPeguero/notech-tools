"""Minimal SNBT reader/writer for FTB Quests files (keeps typed-number suffixes as raw tokens)."""
import re

BS = chr(92)


class Raw(str):
    """Unquoted scalar token kept verbatim (numbers with suffixes, booleans)."""


class TypedList(list):
    def __init__(self, t, items):
        super().__init__(items)
        self.t = t


_ws = re.compile(r'(\s|,)*')
_tok = re.compile(r'[^\s,\[\]{}:"]+')


def loads(s):
    p = Parser(s)
    v = p.value()
    p.skip()
    assert p.i == len(s), f"trailing data at {p.i}"
    return v


class Parser:
    def __init__(s, t):
        s.t, s.i = t, 0

    def skip(s):
        s.i = _ws.match(s.t, s.i).end()

    def value(s):
        s.skip()
        c = s.t[s.i]
        if c == '{':
            return s.obj()
        if c == '[':
            return s.arr()
        if c == '"':
            return s.string()
        m = _tok.match(s.t, s.i)
        s.i = m.end()
        return Raw(m.group())

    def string(s):
        s.i += 1
        out = []
        while True:
            c = s.t[s.i]
            if c == BS:
                out.append(s.t[s.i + 1])
                s.i += 2
                continue
            if c == '"':
                s.i += 1
                return ''.join(out)
            out.append(c)
            s.i += 1

    def obj(s):
        s.i += 1
        d = {}
        while True:
            s.skip()
            if s.t[s.i] == '}':
                s.i += 1
                return d
            if s.t[s.i] == '"':
                k = s.string()
            else:
                m = _tok.match(s.t, s.i)
                k = m.group()
                s.i = m.end()
            s.skip()
            assert s.t[s.i] == ':', (s.i, s.t[s.i - 20:s.i + 20])
            s.i += 1
            d[k] = s.value()

    def arr(s):
        s.i += 1
        s.skip()
        m = re.match(r'([BIL]);', s.t[s.i:])
        t = None
        if m:
            t = m.group(1)
            s.i += 2
        out = []
        while True:
            s.skip()
            if s.t[s.i] == ']':
                s.i += 1
                return TypedList(t, out) if t else out
            out.append(s.value())


_bare = re.compile(r'^[A-Za-z0-9_\-.+]+$')


def q(x):
    return '"' + x.replace(BS, BS + BS).replace('"', BS + '"') + '"'


def dumps(v, ind=0):
    t = '\t'
    if isinstance(v, dict):
        if not v:
            return '{ }'
        lines = [f"{t * (ind + 1)}{k if _bare.match(k) else q(k)}: {dumps(x, ind + 1)}" for k, x in v.items()]
        return '{\n' + '\n'.join(lines) + '\n' + t * ind + '}'
    if isinstance(v, TypedList):
        return f"[{v.t}; " + ', '.join(str(x) for x in v) + ']'
    if isinstance(v, list):
        if not v:
            return '[ ]'
        if all(isinstance(x, Raw) for x in v):
            return '[' + ', '.join(v) + ']'
        if all(isinstance(x, str) for x in v):
            return '[\n' + '\n'.join(t * (ind + 1) + q(x) for x in v) + '\n' + t * ind + ']'
        return '[\n' + '\n'.join(t * (ind + 1) + dumps(x, ind + 1) for x in v) + '\n' + t * ind + ']'
    if isinstance(v, Raw):
        return str(v)
    return q(v)


if __name__ == '__main__':
    import sys
    import glob
    n = 0
    for f in glob.glob(sys.argv[1] + '/**/*.snbt', recursive=True):
        txt = open(f, encoding='utf-8').read()
        a = loads(txt)
        b = loads(dumps(a))
        assert a == b, f
        n += 1
    print('roundtrip ok', n)

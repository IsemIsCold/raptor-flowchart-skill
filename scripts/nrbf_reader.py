"""Minimal MS-NRBF (.NET BinaryFormatter) reader that keeps full record detail.

A RAPTOR .rap file is several BinaryFormatter streams concatenated back to back.
read_streams(data) -> list of streams; each stream is a list of records (dicts).
"""
import struct

PRIM = {1: 'Boolean', 2: 'Byte', 3: 'Char', 5: 'Decimal', 6: 'Double', 7: 'Int16',
        8: 'Int32', 9: 'Int64', 10: 'SByte', 11: 'Single', 12: 'TimeSpan',
        13: 'DateTime', 14: 'UInt16', 15: 'UInt32', 16: 'UInt64', 17: 'Null', 18: 'String'}


class R:
    def __init__(self, d, pos=0):
        self.d, self.p = d, pos

    def u8(self):
        v = self.d[self.p]; self.p += 1; return v

    def i32(self):
        v = struct.unpack_from('<i', self.d, self.p)[0]; self.p += 4; return v

    def fmt(self, f):
        v = struct.unpack_from(f, self.d, self.p)[0]; self.p += struct.calcsize(f); return v

    def lps(self):
        n = 0; shift = 0
        while True:
            b = self.u8(); n |= (b & 0x7f) << shift; shift += 7
            if not b & 0x80: break
        s = self.d[self.p:self.p + n].decode('utf-8'); self.p += n; return s

    def prim(self, t):
        if t == 1: return bool(self.u8())
        if t == 2: return self.u8()
        if t == 3:  # UTF-8 char
            b = self.d[self.p]; n = 1 if b < 0x80 else 2 if b < 0xe0 else 3 if b < 0xf0 else 4
            s = self.d[self.p:self.p + n].decode('utf-8'); self.p += n; return s
        if t == 5: return self.lps()
        f = {6: '<d', 7: '<h', 8: '<i', 9: '<q', 10: '<b', 11: '<f', 12: '<q', 13: '<Q',
             14: '<H', 15: '<I', 16: '<Q'}[t]
        return self.fmt(f)


def read_classinfo(r):
    oid = r.i32(); name = r.lps(); n = r.i32()
    return oid, name, [r.lps() for _ in range(n)]


def read_mti(r, n):
    bts = [r.u8() for _ in range(n)]
    add = []
    for bt in bts:
        if bt in (0, 7): add.append(r.u8())
        elif bt == 3: add.append(r.lps())
        elif bt == 4: add.append((r.lps(), r.i32()))
        else: add.append(None)
    return list(zip(bts, add))


class Stream:
    def __init__(self):
        self.records = []      # top-level records in order
        self.meta = {}         # object id -> (class name, members, types, libid)
        self.libs = {}


def read_value(r, st, bt, add):
    if bt == 0:
        return {'prim': PRIM[add], 'v': r.prim(add)}
    return read_record(r, st)


def read_members(r, st, oid, meta):
    name, members, types, lib = meta
    vals = []
    for m, (bt, add) in zip(members, types):
        vals.append((m, read_value(r, st, bt, add)))
    return vals


def read_record(r, st):
    start = r.p
    t = r.u8()
    if t == 0:
        return {'rt': 'Header', 'root': r.i32(), 'hdr': r.i32(), 'maj': r.i32(), 'min': r.i32()}
    if t == 12:
        lid = r.i32(); nm = r.lps(); st.libs[lid] = nm
        rec = {'rt': 'Library', 'id': lid, 'name': nm}
        return rec
    if t in (4, 5):
        oid, name, members = read_classinfo(r)
        types = read_mti(r, len(members))
        lib = r.i32() if t == 5 else None
        meta = (name, members, types, lib)
        st.meta[oid] = meta
        vals = read_members(r, st, oid, meta)
        return {'rt': 'ClassWithMembersAndTypes' if t == 5 else 'SystemClassWithMembersAndTypes',
                'id': oid, 'class': name, 'lib': lib, 'types': types, 'vals': vals}
    if t == 1:
        oid = r.i32(); mid = r.i32()
        meta = st.meta[mid]
        st.meta[oid] = meta
        vals = read_members(r, st, oid, meta)
        return {'rt': 'ClassWithId', 'id': oid, 'metaid': mid, 'class': meta[0], 'vals': vals}
    if t == 6:
        return {'rt': 'String', 'id': r.i32(), 'v': r.lps()}
    if t == 9:
        return {'rt': 'Ref', 'ref': r.i32()}
    if t == 10:
        return {'rt': 'Null'}
    if t == 13:
        return {'rt': 'NullMultiple256', 'n': r.u8()}
    if t == 14:
        return {'rt': 'NullMultiple', 'n': r.i32()}
    if t == 15:
        oid = r.i32(); n = r.i32(); pt = r.u8()
        if pt == 2:
            v = bytes(r.d[r.p:r.p + n]); r.p += n
        else:
            v = [r.prim(pt) for _ in range(n)]
        return {'rt': 'ArraySinglePrimitive', 'id': oid, 'ptype': PRIM[pt], 'v': v}
    if t == 8:
        pt = r.u8()
        return {'rt': 'MemberPrimitiveTyped', 'ptype': PRIM[pt], 'v': r.prim(pt)}
    if t == 16 or t == 17:
        oid = r.i32(); n = r.i32()
        items = []
        i = 0
        while i < n:
            rec = read_record(r, st)
            items.append(rec)
            if rec['rt'].startswith('NullMultiple'): i += rec['n']
            else: i += 1
        return {'rt': 'ArraySingleObject' if t == 16 else 'ArraySingleString', 'id': oid, 'items': items}
    if t == 7:
        oid = r.i32(); at = r.u8(); rank = r.i32()
        lens = [r.i32() for _ in range(rank)]
        lbs = [r.i32() for _ in range(rank)] if at in (3, 4, 5) else None
        bt = r.u8()
        ((bt, add),) = read_mti_single(r, bt)
        total = 1
        for L in lens: total *= L
        items = []
        i = 0
        while i < total:
            if bt == 0:
                items.append(r.prim(add)); i += 1
            else:
                rec = read_record(r, st); items.append(rec)
                i += rec['n'] if rec['rt'].startswith('NullMultiple') else 1
        return {'rt': 'BinaryArray', 'id': oid, 'atype': at, 'lens': lens, 'bt': bt, 'add': add, 'items': items}
    if t == 11:
        return {'rt': 'End'}
    raise ValueError(f'unknown record type {t} at {start}')


def read_mti_single(r, bt):
    if bt in (0, 7): return [(bt, r.u8())]
    if bt == 3: return [(bt, r.lps())]
    if bt == 4: return [(bt, (r.lps(), r.i32()))]
    return [(bt, None)]


def _fix_byte_arrays(r, rec):
    pass


def read_streams(data):
    r = R(data)
    out = []
    while r.p < len(data):
        st = Stream()
        while True:
            rec = read_record(r, st)
            st.records.append(rec)
            if rec['rt'] == 'End': break
        out.append(st)
    return out, r.p

#!/usr/bin/env python3
"""make_rap.py - build valid RAPTOR flowchart (.rap) files from a simple JSON spec.

Targets the current RAPTOR (the Avalonia version from raptor.martincarlisle.com, the one that
saves .rap files as XML starting with "<MainWindowViewModel.Raptor_File"). The XML is written
exactly the way RAPTOR's own DataContractSerializer writes it, and every symbol's text is checked
with a port of RAPTOR's own parser, because RAPTOR silently blanks any symbol it cannot parse.

Usage:
  python make_rap.py spec.json -o Lab1_Q1.rap     # build (refuses to write if anything is invalid)
  python make_rap.py spec.json --check            # validate only, print the outline
  python make_rap.py --dump existing.rap          # read a .rap (XML or old binary) -> outline + JSON spec
  python make_rap.py --dump existing.rap --json   # JSON spec only (edit it, then build again)

Spec format (full details in the skill's SKILL.md):
  {"subcharts": [{"name": "main", "body": [STATEMENTS]}, {"name": "Helper", "body": [...]},
                 {"name": "Swap", "params": ["in out a", "in out b"], "body": [...]}]}
  STATEMENTS: {"assign": "x", "value": "x + 1"}   {"input": "n", "prompt": "Enter n"}
              {"output": "\\"Total: \\" + t", "newline": true}   {"call": "Helper"}
              {"if": "x > 0", "then": [...], "else": [...]}
              {"while": "i <= 10", "body": [...]}   {"repeat": [...], "until": "x > 0"}
              {"for": "i", "from": "1", "to": "n", "step": "1", "body": [...]}
              {"loop": "<EXIT condition>", "before": [...], "body": [...]}   (raw RAPTOR loop)
              any statement may carry "comment": "text"
"""
import argparse
import json
import os
import re
import sys
import uuid
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import raptor_syntax as rs  # noqa: E402

H, W = 60, 90          # Visual_Flow_Form.flow_height / flow_width
CL = H // 4            # connector length
SER_VERSION = 17       # Component.current_serialization_version

NS_VM = 'http://schemas.datacontract.org/2004/07/RAPTOR_Avalonia_MVVM.ViewModels'
NS_RAPTOR = 'http://schemas.datacontract.org/2004/07/raptor'
NS_I = 'http://www.w3.org/2001/XMLSchema-instance'
NS_XSD = 'http://www.w3.org/2001/XMLSchema'
NS_SER = 'http://schemas.microsoft.com/2003/10/Serialization/'


class SpecError(Exception):
    pass


# ---------------------------------------------------------------------------------------------
# Internal model
# ---------------------------------------------------------------------------------------------
class Node:
    """One flowchart symbol. kind: oval | proc_oval | assign | call | input | output | if | loop"""

    def __init__(self, kind, text='', **kw):
        self.kind = kind
        self.text = text
        self.prompt = kw.get('prompt', '')
        self.new_line = kw.get('new_line', True)
        self.yes = kw.get('yes', [])        # if: then-branch      (list of Node)
        self.no = kw.get('no', [])          # if: else-branch
        self.before = kw.get('before', [])  # loop: runs before the test
        self.after = kw.get('after', [])    # loop: body, runs when the test is FALSE
        self.params = kw.get('params', [])  # proc_oval: [(name, is_in, is_out)]
        self.comment = kw.get('comment')    # str or None
        self.guid = str(uuid.uuid4())
        # layout (filled by layout())
        self.x = self.y = 0
        self.fp = (W // 2, W // 2, H)
        self.geo = {}


class Chart:
    def __init__(self, name, kind='Subchart', params=None):
        self.name = name
        self.kind = kind            # Subchart | Procedure
        self.params = params or []  # [(name, in, out)]
        self.body = []              # list of Node (between start and end)


# ---------------------------------------------------------------------------------------------
# Spec -> model, with friendly normalisation of common AI mistakes
# ---------------------------------------------------------------------------------------------
def _outside_strings(s, fn):
    """apply fn to the parts of s that are not inside "..." string literals or 'c' characters."""
    out, buf, i = [], [], 0
    while i < len(s):
        c = s[i]
        if c == '"':
            out.append(fn(''.join(buf))); buf = []
            j = i + 1
            while j < len(s):
                if s[j] == '"' and (j + 1 >= len(s) or s[j + 1] != '"'):
                    break
                if s[j] == '"':
                    j += 1
                j += 1
            out.append(s[i:j + 1]); i = j + 1
            continue
        if c == "'" and i + 2 < len(s) and s[i + 2] == "'":
            out.append(fn(''.join(buf))); buf = []
            out.append(s[i:i + 3]); i += 3
            continue
        buf.append(c); i += 1
    out.append(fn(''.join(buf)))
    return ''.join(out)


FIXES = [('“', '"'), ('”', '"'), ('‘', "'"), ('’', "'")]
OP_FIXES = [('<>', '!='), ('≠', '!='), ('≤', '<='), ('≥', '>='), ('×', '*'),
            ('÷', '/'), ('−', '-')]


def normalize(text, where, warnings):
    if text is None:
        return ''
    s = str(text).strip()
    orig = s
    for a, b in FIXES:
        s = s.replace(a, b)

    def fix_ops(part):
        for a, b in OP_FIXES:
            part = part.replace(a, b)
        part = re.sub(r'\bAND\b|\bAnd\b', 'and', part)
        part = re.sub(r'\bOR\b|\bOr\b', 'or', part)
        part = re.sub(r'\bNOT\b|\bNot\b', 'not', part)
        return part
    s = _outside_strings(s, fix_ops)
    if s != orig:
        warnings.append('%s: rewrote %r -> %r' % (where, orig, s))
    return s


def split_assign(text):
    for op in (':=', '←', '<-', '='):
        if op in text:
            a, b = text.split(op, 1)
            return a.strip(), b.strip()
    raise SpecError('assignment %r has no ":=" (expected {"assign": "x", "value": "expr"})' % text)


def invert_condition(cond):
    """while-condition -> RAPTOR loop exit-condition (RAPTOR loops EXIT when the test is TRUE)."""
    lx = rs.Lexer(cond)
    toks, depth, rel, logic = [], 0, [], False
    try:
        while True:
            t = lx.get()
            if t.kind == 'End_Input':
                break
            if t.kind == 'Left_Paren':
                depth += 1
            elif t.kind == 'Right_Paren':
                depth -= 1
            elif depth == 0 and t.kind in ('And', 'Or', 'Xor', 'Not'):
                logic = True
            elif depth == 0 and rs.is_relation(t.kind):
                rel.append(t)
            toks.append(t)
    except rs.SyntaxErr:
        return 'not (%s)' % cond
    swap = {'Greater': '<=', 'Greater_Equal': '<', 'Less': '>=', 'Less_Equal': '>', 'Equal': '!=',
            'Not_Equal': '='}
    if len(rel) == 1 and not logic:
        t = rel[0]
        return (cond[:t.start].rstrip() + ' ' + swap[t.kind] + ' ' + cond[t.finish + 1:].lstrip()).strip()
    return 'not (%s)' % cond


def to_param(p, where):
    if isinstance(p, str):
        m = re.match(r'^\s*(in\s+out|inout|in|out)?\s*([A-Za-z]\w*)\s*$', p)
        if not m:
            raise SpecError('%s: bad parameter %r (use "in x", "out y" or "in out z")' % (where, p))
        mode = (m.group(1) or 'in').replace(' ', '')
        return (m.group(2), 'in' in mode, 'out' in mode)
    return (p['name'], bool(p.get('in', True)), bool(p.get('out', False)))


def build_stmts(items, where, warnings):
    if items is None:
        return []
    if isinstance(items, dict):
        items = [items]
    out = []
    for i, st in enumerate(items):
        out.extend(build_stmt(st, '%s[%d]' % (where, i), warnings))
    return out


def build_stmt(st, where, warnings):
    if isinstance(st, str):
        raise SpecError('%s: statement must be an object like {"assign": "x", "value": "1"}, got %r' % (where, st))
    comment = st.get('comment')
    nodes = []
    if 'assign' in st or 'set' in st:
        var = st.get('assign', st.get('set'))
        val = st.get('value', st.get('to', st.get('expr')))
        if val is None:
            var, val = split_assign(str(var))
        var = normalize(var, where, warnings)
        val = normalize(val, where, warnings)
        nodes = [Node('assign', '%s:=%s' % (var, val))]
    elif 'call' in st:
        nodes = [Node('call', normalize(st['call'], where, warnings))]
    elif 'input' in st:
        var = normalize(st['input'], where, warnings)
        prompt = st.get('prompt', '')
        prompt = '' if prompt is None else str(prompt)
        if st.get('prompt_is_expression') or '"' in prompt:
            prompt = normalize(prompt, where, warnings)
        else:  # plain text -> string literal, exactly like RAPTOR's Input dialog does
            prompt = '"' + prompt.replace('"', '""') + '"'
        nodes = [Node('input', var, prompt=prompt)]
    elif 'output' in st:
        nodes = [Node('output', normalize(st['output'], where, warnings), new_line=bool(st.get('newline', True)))]
    elif 'if' in st:
        nodes = [Node('if', normalize(st['if'], where, warnings),
                      yes=build_stmts(st.get('then'), where + '.then', warnings),
                      no=build_stmts(st.get('else'), where + '.else', warnings))]
    elif 'loop' in st or 'exit_when' in st:
        cond = st.get('loop', st.get('exit_when'))
        nodes = [Node('loop', normalize(cond, where, warnings),
                      before=build_stmts(st.get('before'), where + '.before', warnings),
                      after=build_stmts(st.get('body', st.get('after')), where + '.body', warnings))]
    elif 'while' in st:
        cond = normalize(st['while'], where, warnings)
        nodes = [Node('loop', invert_condition(cond),
                      after=build_stmts(st.get('body', st.get('do')), where + '.body', warnings))]
    elif 'repeat' in st:
        if 'until' not in st:
            raise SpecError('%s: "repeat" needs "until": "<condition that ends the loop>"' % where)
        nodes = [Node('loop', normalize(st['until'], where, warnings),
                      before=build_stmts(st['repeat'], where + '.repeat', warnings))]
    elif 'for' in st:
        var = normalize(st['for'], where, warnings)
        start = normalize(st.get('from', '1'), where, warnings)
        stop = normalize(st.get('to'), where, warnings)
        step = normalize(st.get('step', '1'), where, warnings)
        if not stop:
            raise SpecError('%s: "for" needs "to"' % where)
        down = step.startswith('-')
        exit_cond = '%s %s %s' % (var, '<' if down else '>', stop)
        incr = '%s:=%s - %s' % (var, var, step[1:].strip()) if down else '%s:=%s + %s' % (var, var, step)
        body = build_stmts(st.get('body', st.get('do')), where + '.body', warnings) + [Node('assign', incr)]
        nodes = [Node('assign', '%s:=%s' % (var, start)), Node('loop', exit_cond, after=body)]
    else:
        raise SpecError('%s: unknown statement %s (use assign, input, output, call, if, while, '
                        'repeat/until, for, loop)' % (where, json.dumps(st)[:120]))
    if comment:
        nodes[0].comment = str(comment)
    return nodes


def build_charts(spec, warnings):
    if isinstance(spec, list):
        spec = {'subcharts': [{'name': 'main', 'body': spec}]}
    if 'subcharts' not in spec:
        spec = {'subcharts': [{'name': spec.get('name', 'main'), 'body': spec.get('body', spec.get('main', []))}]
                + spec.get('extra_subcharts', [])}
    charts = []
    for i, sc in enumerate(spec['subcharts']):
        name = str(sc.get('name', 'main' if i == 0 else 'sub%d' % i)).strip()
        params = [to_param(p, name) for p in sc.get('params', [])]
        kind = 'Procedure' if ('params' in sc and i > 0) else 'Subchart'
        c = Chart(name, kind, params)
        c.body = build_stmts(sc.get('body', []), name, warnings)
        charts.append(c)
    return charts


# ---------------------------------------------------------------------------------------------
# Validation (the same checks RAPTOR runs when it opens the file, plus run-time pitfalls)
# ---------------------------------------------------------------------------------------------
IDENT = re.compile(r'^[A-Za-z][A-Za-z0-9_]*$')


def validate(charts):
    errors, warnings = [], []
    names = [c.name for c in charts]
    if not charts:
        errors.append('no subcharts')
        return errors, warnings
    if charts[0].kind != 'Subchart':
        errors.append('the first subchart is the main chart and cannot have parameters')
    if charts[0].name.lower() != 'main':
        warnings.append('first subchart is named %r; RAPTOR always treats the first tab as main' % charts[0].name)
    seen = set()
    for c in charts:
        if not IDENT.match(c.name):
            errors.append('subchart name %r must start with a letter and use only letters, digits, _' % c.name)
        elif rs.reserved_word(c.name) and c is not charts[0]:
            errors.append('subchart name %r is a RAPTOR built-in name (%s); pick another'
                          % (c.name, rs.reserved_word(c.name)))
        if c.name.lower() in seen:
            errors.append('duplicate subchart name %r' % c.name)
        seen.add(c.name.lower())
        for (p, _, _) in c.params:
            if rs.reserved_word(p):
                errors.append('%s: parameter %r is a RAPTOR built-in name; rename it' % (c.name, p))
    procs = {c.name: c for c in charts[1:]}
    callable_names = names[1:]

    def check_chain(nodes, where):
        for i, n in enumerate(nodes):
            w = '%s[%d] %s' % (where, i, n.kind)
            err = None
            if n.kind == 'assign':
                var, expr = n.text.split(':=', 1)
                if not expr.strip():
                    err = 'assignment has no value'
                else:
                    err = rs.check_assignment(var, expr, callable_names)
                    target = re.match(r'\s*([A-Za-z]\w*)', var)
                    if not err and target and target.group(1) in procs:
                        err = '%r is a subchart name and cannot also be a variable' % target.group(1)
            elif n.kind == 'call':
                err = rs.check_call(n.text, callable_names)
                m = re.match(r'\s*([A-Za-z]\w*)\s*(?:\((.*)\))?\s*;?\s*$', n.text, re.S)
                if not err and m and m.group(1) in procs:
                    target = procs[m.group(1)]
                    nargs = 0 if not (m.group(2) or '').strip() else len(_split_args(m.group(2)))
                    if nargs != len(target.params):
                        err = '%s takes %d argument(s), call passes %d' % (target.name, len(target.params), nargs)
            elif n.kind == 'input':
                err = rs.check_input(n.text)
                if not err:
                    perr = rs.check_output(n.prompt)
                    if perr:
                        err = 'prompt %s: %s' % (n.prompt, perr)
            elif n.kind == 'output':
                err = rs.check_output(n.text)
            elif n.kind in ('if', 'loop'):
                if not n.text:
                    err = 'empty condition'
                else:
                    err = rs.check_condition(n.text)
            if err:
                errors.append('%s %r: %s' % (w, n.text, err))
            if n.kind == 'if':
                check_chain(n.yes, w + '.then')
                check_chain(n.no, w + '.else')
            if n.kind == 'loop':
                check_chain(n.before, w + '.before')
                check_chain(n.after, w + '.body')
                if not n.before and not n.after:
                    warnings.append('%s: loop has an empty body' % w)
    for c in charts:
        check_chain(c.body, c.name)
    if not errors:
        warnings += unassigned_warnings(charts)
    return errors, warnings


def _idents(text):
    """identifier tokens (variables) in a RAPTOR text, skipping keywords and string literals."""
    out, lx = [], rs.Lexer(text)
    try:
        while True:
            t = lx.get()
            if t.kind == 'End_Input':
                return out
            if t.kind == 'Id':
                out.append(lx.text(t))
    except rs.SyntaxErr:
        return out


def unassigned_warnings(charts):
    """warn about variables that are read somewhere but never assigned or input (usually a typo)."""
    sub_names = {c.name for c in charts}
    scopes = {}  # main + plain subcharts share one scope; each procedure has its own

    def scope_of(c):
        return c.name if c.kind == 'Procedure' else '__global__'

    def walk(nodes, sc):
        for n in nodes:
            if n.kind in ('assign', 'input'):
                lhs = n.text.split(':=', 1)[0] if n.kind == 'assign' else n.text
                ids = _idents(lhs)
                if ids:
                    sc['set'].add(ids[0])
                    sc['use'] += [(i, n.text) for i in ids[1:]]  # array indexes
                if n.kind == 'assign':
                    sc['use'] += [(i, n.text) for i in _idents(n.text.split(':=', 1)[1])]
                else:
                    sc['use'] += [(i, n.prompt) for i in _idents(n.prompt)]
            elif n.kind == 'call':
                ids = _idents(n.text)
                if ids and ids[0] in sub_names:
                    target = next(c for c in charts if c.name == ids[0])
                    args = _split_args(re.sub(r'^[^(]*\(|\)\s*;?\s*$', '', n.text)) if '(' in n.text else []
                    for (p, pin, pout), arg in zip(target.params, args):
                        a = _idents(arg)
                        if pout and a:
                            sc['set'].add(a[0])
                        if pin:
                            sc['use'] += [(i, n.text) for i in a]
                    ids = []
                elif re.match(r'\s*get_mouse_button\s*\(', n.text, re.I):
                    # Get_Mouse_Button(button, x, y) stores the click position in x and y
                    args = _split_args(re.sub(r'^[^(]*\(|\)\s*;?\s*$', '', n.text))
                    for arg in args[1:3]:
                        a = _idents(arg)
                        if a:
                            sc['set'].add(a[0])
                    sc['use'] += [(i, n.text) for i in _idents(args[0])]
                    ids = []
                sc['use'] += [(i, n.text) for i in ids]
            elif n.kind in ('output', 'if', 'loop'):
                sc['use'] += [(i, n.text) for i in _idents(n.text)]
            walk(n.yes + n.no + n.before + n.after, sc)
    for c in charts:
        sc = scopes.setdefault(scope_of(c), {'set': set(), 'use': []})
        sc['set'].update(p for p, _, _ in c.params)
        walk(c.body, sc)
    out = []
    for name, sc in scopes.items():
        seen = set()
        for var, text in sc['use']:
            if var not in sc['set'] and var not in sub_names and var not in seen:
                seen.add(var)
                out.append('variable %r is used (in %r) but never assigned or input%s - typo, or missing '
                           'initialisation?' % (var, text, '' if name == '__global__' else ' in procedure ' + name))
    return out


def _split_args(s):
    parts, depth, cur, q = [], 0, '', False
    for ch in s:
        if ch == '"':
            q = not q
        if not q:
            if ch in '([':
                depth += 1
            elif ch in ')]':
                depth -= 1
            elif ch == ',' and depth == 0:
                parts.append(cur); cur = ''
                continue
        cur += ch
    parts.append(cur)
    return parts


# ---------------------------------------------------------------------------------------------
# Layout - RAPTOR recomputes all geometry when it draws, so this only needs to be sensible.
# ---------------------------------------------------------------------------------------------
def chain_size(nodes):
    """(left, right, height) of a chain of nodes."""
    if not nodes:
        return (W // 2, W // 2, 0)
    left = right = 0
    height = 0
    for n in nodes:
        l, r, h = node_size(n)
        left, right = max(left, l), max(right, r)
        height += h
    height += CL * (len(nodes) - 1)
    return left, right, height


def node_size(n):
    if n.kind == 'if':
        yl, yr, yh = chain_size(n.yes)
        nl, nr, nh = chain_size(n.no)
        left = max(W, yl + yr + W // 4)
        right = max(W, nl + nr + W // 4)
        return left, right, H + H // 2 + max(yh, nh) + H // 2
    if n.kind == 'loop':
        bl, br, bh = chain_size(n.before)
        al, ar, ah = chain_size(n.after)
        return max(W, bl, al) + W // 4, max(W, br, ar) + W // 4, 2 * H + H // 2 + bh + ah + H // 2 + H // 2
    return W // 2, W // 2, H


def layout_chain(nodes, x, y):
    for idx, n in enumerate(nodes):
        n.x, n.y = x, y
        l, r, h = chain_size(nodes[idx:])
        n.fp = (l, r, h)
        nl, nr, nh = node_size(n)
        if n.kind == 'if':
            yl, yr, _ = chain_size(n.yes)
            ol, orr, _ = chain_size(n.no)
            xl, xr = x - nl + yl, x + nr - orr
            n.geo = dict(bottom=y + nh - H // 2, min_bottom=y + nh - H // 2, x_left=xl, y_left=y + H,
                         x_right=xr, y_right=y + H, left_connector_y=y + H // 2, right_connector_y=y + H // 2,
                         line_height=nh - H)
            layout_chain(n.yes, xl, y + H + H // 2)
            layout_chain(n.no, xr, y + H + H // 2)
        elif n.kind == 'loop':
            _, _, bh = chain_size(n.before)
            _, _, ah = chain_size(n.after)
            diamond_top = y + H // 2 + bh + (CL if n.before else 0)
            n.geo = dict(bottom=y + nh, min_before_bottom=y + H // 2 + bh, before_bottom=diamond_top,
                         after_bottom=diamond_top + H + H // 2 + ah, x_left=x - nl, y_left=y,
                         x_right=x + nr, y_right=y, left_connector_y=y, right_connector_y=y, line_height=nh)
            layout_chain(n.before, x, y + H // 2)
            layout_chain(n.after, x, diamond_top + H + H // 2)
        y += nh + CL


# ---------------------------------------------------------------------------------------------
# XML writer - byte-compatible with RAPTOR's DataContractSerializer output
# ---------------------------------------------------------------------------------------------
def _x(top):
    return ' xmlns=""' if top else ''


def e_prim(name, typ, val, top):
    if typ == 'string' and val == '':
        return '<%s i:type="b:string"%s xmlns:b="%s"/>' % (name, _x(top), NS_XSD)
    return '<%s i:type="b:%s"%s xmlns:b="%s">%s</%s>' % (name, typ, _x(top), NS_XSD, val, name)


def e_int(name, v, top):
    return e_prim(name, 'int', str(int(v)), top)


def e_bool(name, v, top):
    return e_prim(name, 'boolean', 'true' if v else 'false', top)


def e_str(name, v, top):
    return e_prim(name, 'string', escape(v), top)


def e_nil(name, top):
    return '<%s i:nil="true"%s/>' % (name, _x(top))


def e_guid(name, g, top):
    return '<%s i:type="b:guid"%s xmlns:b="%s">%s</%s>' % (name, _x(top), NS_SER, g, name)


def e_fp(fp, top):
    l, r, h = fp
    return ('<_FP i:type="a:Component.FootPrint"%s><a:height>%d</a:height><a:left>%d</a:left>'
            '<a:right>%d</a:right></_FP>' % (_x(top), h, l, r))


CLASS = {'oval': 'Oval', 'proc_oval': 'Oval_Procedure', 'assign': 'Rectangle', 'call': 'Rectangle',
         'input': 'Parallelogram', 'output': 'Parallelogram', 'if': 'IF_Control', 'loop': 'Loop'}


def e_obj(name, nodes, top, flags):
    if not nodes:
        return e_nil(name, top)
    return '<%s i:type="a:%s"%s>%s</%s>' % (name, CLASS[nodes[0].kind], _x(top),
                                            component_entries(nodes, 0, False, flags), name)


def e_comment(text, top):
    lines = text.split('\n')
    parts = ['<_comment i:type="a:CommentBox"%s>' % _x(top),
             e_int('_num_lines', len(lines), False), e_int('_x_location', W, False),
             e_int('_y_location', -10, False), e_int('_version', SER_VERSION, False)]
    parts += [e_str('_line%d' % i, ln, False) for i, ln in enumerate(lines)]
    parts.append('</_comment>')
    return ''.join(parts)


def component_entries(nodes, i, top, flags):
    """the ISerializable entries of nodes[i] (its successor chain nested inside _Successor)."""
    n = nodes[i]
    is_child, is_before, is_after = flags
    out = []
    g = n.geo
    if n.kind in ('input', 'output'):
        out += [e_str('_prompt', n.prompt if n.kind == 'input' else '', top),
                e_bool('_is_input', n.kind == 'input', top),
                e_bool('_new_line', n.new_line, top),
                e_bool('_input_expression', n.kind == 'input', top)]
    elif n.kind == 'if':
        cf = (True, False, False)
        out += [e_obj('_left_Child', n.yes, top, cf), e_obj('_right_Child', n.no, top, cf)]
        out += [e_int('_' + k, g[k], top) for k in ('bottom', 'min_bottom', 'x_left', 'y_left', 'x_right',
                                                     'y_right', 'left_connector_y', 'right_connector_y',
                                                     'line_height')]
        out.append(e_bool('_is_compressed', False, top))
    elif n.kind == 'loop':
        out += [e_obj('_before_Child', n.before, top, (True, True, False)),
                e_obj('_after_Child', n.after, top, (True, False, True))]
        out += [e_int('_' + k, g[k], top) for k in ('bottom', 'min_before_bottom', 'before_bottom',
                                                     'after_bottom', 'x_left', 'y_left', 'x_right', 'y_right',
                                                     'left_connector_y', 'right_connector_y', 'line_height')]
        out += [e_str('_LP', 'Loop', top), e_bool('_is_compressed', False, top)]
    has_succ = i + 1 < len(nodes)
    out += [e_int('_serialization_version', SER_VERSION, top), e_fp(n.fp, top),
            e_str('_text_str', n.text, top),
            e_str('_name', {'oval': 'Oval', 'proc_oval': 'Oval'}.get(n.kind, CLASS[n.kind]), top),
            e_int('_proximity', 10, top), e_int('_head_height', H, top), e_int('_head_width', W, top),
            e_int('_head_heightOrig', H, top), e_int('_head_widthOrig', W, top),
            e_int('_connector_length', CL if has_succ else 0, top),
            e_int('_x_location', n.x, top), e_int('_y_location', n.y, top)]
    if has_succ:
        out.append('<_Successor i:type="a:%s"%s>%s</_Successor>' % (
            CLASS[nodes[i + 1].kind], _x(top), component_entries(nodes, i + 1, False, flags)))
    else:
        out.append(e_nil('_Successor', top))
    out += [e_bool('_is_child', is_child, top), e_bool('_is_beforeChild', is_before, top),
            e_bool('_is_afterChild', is_after, top), e_bool('_full_text', True, top),
            e_int('_height_of_text', 14, top), e_int('_char_length', 0, top)]
    out.append(e_comment(n.comment, top) if n.comment else e_nil('_comment', top))
    out += [e_guid('_created_guid', n.guid, top), e_guid('_changed_guid', n.guid, top)]
    if n.kind in ('assign', 'call'):
        out.append('<_kind i:type="a:Rectangle.Kind_Of"%s>%s</_kind>' % (
            _x(top), 'Call' if n.kind == 'call' else 'Assignment'))
    if n.kind == 'proc_oval':
        out.append(e_int('_numparams', len(n.params), top))
        for k, (pname, pin, pout) in enumerate(n.params):
            out += [e_str('_paramname%d' % k, pname, top), e_bool('_paraminput%d' % k, pin, top),
                    e_bool('_paramoutput%d' % k, pout, top)]
    return ''.join(out)


def chart_nodes(c):
    if c.kind == 'Procedure':
        start = Node('proc_oval', 'Start (' + ','.join(
            ('in ' if pin else '') + ('out ' if pout else '') + p for p, pin, pout in c.params) + ')',
            params=c.params)
    else:
        start = Node('oval', 'start')
    return [start] + c.body + [Node('oval', 'end')]


def to_xml(charts, file_guid=None):
    parts = ['<MainWindowViewModel.Raptor_File xmlns="%s" xmlns:i="%s">' % (NS_VM, NS_I),
             '<FileGuid>%s</FileGuid>' % (file_guid or uuid.uuid4()),
             '<log xmlns:a="%s">' % NS_RAPTOR, e_int('_serialization_version', SER_VERSION, True),
             e_int('_count', 0, True), '</log>', '<subcharts xmlns:a="%s">' % NS_RAPTOR]
    for c in charts:
        nodes = chart_nodes(c)
        x0 = max(chain_size(nodes)[0] + W // 3, W)
        layout_chain(nodes, x0, 30)
        start_type = ' i:type="a:Oval_Procedure"' if c.kind == 'Procedure' else ''
        parts.append('<a:Subchart><a:Start%s>%s</a:Start><a:Text>%s</a:Text><a:kind>%s</a:kind></a:Subchart>'
                     % (start_type, component_entries(nodes, 0, True, (False, False, False)),
                        escape(c.name), c.kind))
    parts.append('</subcharts></MainWindowViewModel.Raptor_File>')
    return ''.join(parts)


# ---------------------------------------------------------------------------------------------
# Reading existing .rap files (XML from current RAPTOR, or binary from classic RAPTOR 4.x)
# ---------------------------------------------------------------------------------------------
def read_rap(path):
    data = open(path, 'rb').read()
    if data.lstrip(b'\xef\xbb\xbf \r\n\t')[:1] == b'<':
        return read_xml(data)
    return read_binary(data)


def read_xml(data):
    import xml.etree.ElementTree as ET
    root = ET.fromstring(data.decode('utf-8-sig'))
    ra = '{%s}' % NS_RAPTOR
    itype = '{%s}type' % NS_I
    inil = '{%s}nil' % NS_I

    def ent(el):
        return {ch.tag.split('}')[-1]: ch for ch in el}

    def val(el):
        if el is None or el.get(inil) == 'true':
            return None
        return el.text or ''

    def comp(el):
        if el is None or el.get(inil) == 'true':
            return None
        t = (el.get(itype) or 'a:Oval').split(':')[-1]
        e = ent(el)
        d = {'class': t, 'text': val(e.get('_text_str')) or ''}
        if t == 'Rectangle':
            d['kind'] = val(e.get('_kind'))
        if t == 'Parallelogram':
            d['is_input'] = val(e.get('_is_input')) == 'true'
            d['prompt'] = val(e.get('_prompt')) or ''
            d['new_line'] = val(e.get('_new_line')) != 'false'
        if t == 'IF_Control':
            d['yes'] = comp(e.get('_left_Child'))
            d['no'] = comp(e.get('_right_Child'))
        if t == 'Loop':
            d['before'] = comp(e.get('_before_Child'))
            d['after'] = comp(e.get('_after_Child'))
        if t == 'Oval_Procedure':
            n = int(val(e.get('_numparams')) or 0)
            d['params'] = [(val(e.get('_paramname%d' % k)), val(e.get('_paraminput%d' % k)) == 'true',
                            val(e.get('_paramoutput%d' % k)) == 'true') for k in range(n)]
        c = e.get('_comment')
        if c is not None and c.get(inil) != 'true':
            ce = ent(c)
            d['comment'] = '\n'.join(val(ce.get('_line%d' % k)) or '' for k in range(int(val(ce.get('_num_lines')) or 0)))
        d['next'] = comp(e.get('_Successor'))
        return d

    charts = []
    for sc in root.iter(ra + 'Subchart'):
        e = {ch.tag.split('}')[-1]: ch for ch in sc}
        charts.append({'name': (e['Text'].text or ''), 'kind': e['kind'].text if 'kind' in e else 'Subchart',
                       'start': comp(e.get('Start'))})
    return charts


def read_binary(data):
    try:
        import nrbf_reader as nr
    except ImportError:
        raise SystemExit('This is an old binary .rap (classic RAPTOR 4.x). Reading it needs nrbf_reader.py '
                         '(in the skill zip) next to make_rap.py.')
    streams, _ = nr.read_streams(data)

    def scalar(st):
        for r in st.records:
            if r['rt'] == 'String':
                return r['v']
            if r['rt'] in ('SystemClassWithMembersAndTypes', 'ClassWithMembersAndTypes', 'ClassWithId'):
                if len(r['vals']) == 1:
                    return r['vals'][0][1]['v']
                return r
        return None

    vals = [scalar(s) for s in streams]
    version, k = vals[0], 1
    if version >= 13:
        k += 1
    npages = vals[k]; k += 1
    pages = []
    for i in range(npages):
        name = vals[k]; k += 1
        kind = vals[k] if version >= 14 else 0; k += 1 if version >= 14 else 0
        if i > 0 and kind in (1, 2) and (kind == 2 or version >= 15):
            k += 1
        pages.append((name, ['Subchart', 'Procedure', 'Function', 'UML'][kind]))
    charts = []
    for i in range(npages):
        st = streams[k]; k += 1
        if version >= 17:
            k += 1  # ink bytes
        objs, strs = {}, {}

        def collect(r):
            if isinstance(r, dict):
                if r.get('rt') in ('ClassWithMembersAndTypes', 'SystemClassWithMembersAndTypes', 'ClassWithId'):
                    objs[r['id']] = r
                if r.get('rt') == 'String':
                    strs[r['id']] = r['v']
                for key in ('vals',):
                    for _, v in r.get(key, []):
                        collect(v)
        for r in st.records:
            collect(r)

        def deref(v):
            if v is None or v.get('rt') == 'Null':
                return None
            if v.get('rt') == 'Ref':
                return objs.get(v['ref']) or strs.get(v['ref'])
            if v.get('rt') == 'String':
                return v['v']
            if 'prim' in v:
                return v['v']
            return v

        def comp(o):
            if o is None:
                return None
            m = {name: v for name, v in o['vals']}
            t = o['class'].split('.')[-1]
            d = {'class': t, 'text': deref(m.get('_text_str')) or ''}
            if t == 'Rectangle':
                kind = deref(m.get('_kind'))
                d['kind'] = 'Call' if isinstance(kind, dict) and kind['vals'][0][1]['v'] == 1 else 'Assignment'
            if t == 'Parallelogram':
                d['is_input'] = deref(m.get('_is_input'))
                d['prompt'] = deref(m.get('_prompt')) or ''
                d['new_line'] = deref(m.get('_new_line')) is not False
            if t == 'IF_Control':
                d['yes'] = comp(deref(m.get('_left_Child')))
                d['no'] = comp(deref(m.get('_right_Child')))
            if t == 'Loop':
                d['before'] = comp(deref(m.get('_before_Child')))
                d['after'] = comp(deref(m.get('_after_Child')))
            if t == 'Oval_Procedure':
                n = deref(m.get('_numparams')) or 0
                d['params'] = [(deref(m.get('_paramname%d' % j)), deref(m.get('_paraminput%d' % j)),
                                deref(m.get('_paramoutput%d' % j))) for j in range(n)]
            d['next'] = comp(deref(m.get('_Successor')))
            return d
        root = next(r for r in st.records if r.get('rt') in ('ClassWithMembersAndTypes', 'ClassWithId'))
        charts.append({'name': pages[i][0], 'kind': pages[i][1], 'start': comp(root)})
    return charts


def list_to_spec(c):
    out = []
    while c is not None:
        out.append(comp_to_spec(c))
        c = c.get('next')
    return out


def comp_to_spec(d):
    t, text = d['class'], d['text']
    if t == 'Rectangle':
        if d.get('kind') == 'Call':
            s = {'call': text}
        else:
            var, _, val = text.partition(':=')
            s = {'assign': var.strip(), 'value': val.strip()}
    elif t == 'Parallelogram':
        if d['is_input']:
            s = {'input': text, 'prompt': d['prompt']}  # contains " -> kept as an expression on rebuild
        else:
            s = {'output': text}
            if not d['new_line']:
                s['newline'] = False
    elif t == 'IF_Control':
        s = {'if': text, 'then': list_to_spec(d['yes']), 'else': list_to_spec(d['no'])}
    elif t == 'Loop':
        s = {'loop': text, 'before': list_to_spec(d['before']), 'body': list_to_spec(d['after'])}
        if not s['before']:
            del s['before']
    else:
        s = {'oval': text}
    if d.get('comment'):
        s['comment'] = d['comment']
    return s


def charts_to_spec(charts):
    subs = []
    for c in charts:
        start = c['start']
        body = list_to_spec(start['next'] if start else None)
        if body and body[-1].get('oval') is not None:
            body = body[:-1]
        sc = {'name': c['name'], 'body': body}
        if start and start['class'] == 'Oval_Procedure':
            sc['params'] = [('in ' if i else '') + ('out ' if o else '') + n for n, i, o in start['params']]
        subs.append(sc)
    return {'subcharts': subs}


# ---------------------------------------------------------------------------------------------
# Outline printer (human-readable view of what will be / is in the file)
# ---------------------------------------------------------------------------------------------
def outline_spec(spec):
    lines = []

    def walk(items, ind):
        for s in items:
            p = '  ' * ind
            cm = ('    // ' + s['comment'].replace('\n', ' / ')) if s.get('comment') else ''
            if 'assign' in s:
                lines.append('%s%s <- %s%s' % (p, s['assign'], s.get('value', ''), cm))
            elif 'call' in s:
                lines.append('%sCALL %s%s' % (p, s['call'], cm))
            elif 'input' in s:
                lines.append('%sINPUT %s   (prompt %s)%s' % (p, s['input'], s.get('prompt', ''), cm))
            elif 'output' in s:
                lines.append('%sOUTPUT %s%s%s' % (p, s['output'], '' if s.get('newline', True) else '  (no newline)', cm))
            elif 'if' in s:
                lines.append('%sIF %s THEN%s' % (p, s['if'], cm))
                walk(s.get('then', []), ind + 1)
                if s.get('else'):
                    lines.append('%sELSE' % p)
                    walk(s['else'], ind + 1)
                lines.append('%sEND IF' % p)
            elif 'loop' in s:
                lines.append('%sLOOP%s' % (p, cm))
                walk(s.get('before', []), ind + 1)
                lines.append('%s  EXIT WHEN %s' % (p, s['loop']))
                walk(s.get('body', []), ind + 1)
                lines.append('%sEND LOOP' % p)
    for sc in spec['subcharts']:
        ps = '(%s)' % ', '.join(sc['params']) if sc.get('params') else ''
        lines.append('=== %s%s' % (sc['name'], ps))
        walk(sc['body'], 1)
    return '\n'.join(lines)


def model_to_spec(charts):
    def n2s(n):
        if n.kind == 'assign':
            v, _, e = n.text.partition(':=')
            s = {'assign': v, 'value': e}
        elif n.kind == 'call':
            s = {'call': n.text}
        elif n.kind == 'input':
            s = {'input': n.text, 'prompt': n.prompt}
        elif n.kind == 'output':
            s = {'output': n.text, 'newline': n.new_line}
        elif n.kind == 'if':
            s = {'if': n.text, 'then': [n2s(x) for x in n.yes], 'else': [n2s(x) for x in n.no]}
        else:
            s = {'loop': n.text, 'before': [n2s(x) for x in n.before], 'body': [n2s(x) for x in n.after]}
        if n.comment:
            s['comment'] = n.comment
        return s
    return {'subcharts': [{'name': c.name, 'body': [n2s(n) for n in c.body],
                           **({'params': [('in ' if i else '') + ('out ' if o else '') + p for p, i, o in c.params]}
                              if c.kind == 'Procedure' else {})} for c in charts]}


# ---------------------------------------------------------------------------------------------
def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors='replace')  # e.g. Chinese Windows consoles (GBK)
        except Exception:
            pass
    ap = argparse.ArgumentParser(description='Build or inspect RAPTOR .rap flowchart files.')
    ap.add_argument('spec', nargs='?', help='JSON spec file ("-" for stdin)')
    ap.add_argument('-o', '--output', help='output .rap path')
    ap.add_argument('--check', action='store_true', help='validate only')
    ap.add_argument('--dump', metavar='RAP', help='read an existing .rap file and print its outline')
    ap.add_argument('--json', action='store_true', help='with --dump: print the JSON spec')
    ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args(argv)

    if a.dump:
        spec = charts_to_spec(read_rap(a.dump))
        print(json.dumps(spec, indent=2, ensure_ascii=False) if a.json else outline_spec(spec))
        return 0
    if not a.spec:
        ap.error('give a spec file, or --dump file.rap')
    raw = sys.stdin.read() if a.spec == '-' else open(a.spec, encoding='utf-8-sig').read()
    try:
        spec = json.loads(raw)
    except json.JSONDecodeError as e:
        print('ERROR: spec is not valid JSON: %s' % e)
        return 2
    warnings = []
    try:
        charts = build_charts(spec, warnings)
    except SpecError as e:
        print('ERROR: %s' % e)
        return 2
    errors, w2 = validate(charts)
    warnings += w2
    if not a.quiet:
        print(outline_spec(model_to_spec(charts)))
        print()
    for w in warnings:
        print('warning: ' + w)
    if errors:
        for e in errors:
            print('ERROR: ' + e)
        print('\n%d error(s) - RAPTOR would blank these symbols or refuse them. Nothing written.' % len(errors))
        return 1
    if a.check or not a.output:
        print('OK: spec is valid RAPTOR.' + ('' if a.output else ' (use -o file.rap to write it)'))
        return 0
    xml = to_xml(charts)
    with open(a.output, 'w', encoding='utf-8', newline='') as f:
        f.write(xml)
    print('OK: wrote %s (%d bytes, %d subchart(s))' % (a.output, len(xml.encode('utf-8')), len(charts)))
    return 0


if __name__ == '__main__':
    sys.exit(main())

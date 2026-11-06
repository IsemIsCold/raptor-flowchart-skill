"""RAPTOR expression/statement syntax checker.

A faithful Python port of RAPTOR's own Lexer.cs + Parser.cs (RAPTOR Avalonia,
carlislemc/RAPTOR_Avalonia_MVVM). RAPTOR re-parses the text of every symbol when it
opens a .rap file and silently BLANKS any symbol whose text does not parse, so every
string we put in a file must pass these checks.

Public API (each returns None if valid, or an error message string):
    check_assignment(var, expr, subcharts=())
    check_call(text, subcharts=())          # subcharts = names of the other tabs
    check_condition(text)
    check_input(var_text)
    check_output(expr)
    check_expression(expr)                  # prompt expressions
"""

# Token_Type enum, in the exact order of Lexer.cs (ranges below depend on the order).
TOKENS = ['Plus', 'Minus', 'Times', 'Divide', 'Exponent', 'Left_Paren', 'Right_Paren', 'Id', 'Number',
          'Character', 'String', 'Comma', 'Semicolon', 'Colon_Equal', 'Left_Bracket', 'Right_Bracket',
          'End_Input', 'New', 'Dot', 'Equal', 'Greater', 'Less', 'Not_Equal', 'Greater_Equal', 'Less_Equal',
          'And', 'Or', 'Xor', 'Not', 'Mod', 'Rem', 'Sin', 'Cos', 'Tan', 'Cot', 'Arcsin', 'Arccos', 'Log',
          'Arctan', 'Arccot', 'Min', 'Max', 'Sinh', 'Tanh', 'Cosh', 'Arccosh', 'Arcsinh', 'Arctanh', 'Coth',
          'Arccoth', 'Sqrt', 'Floor', 'Ceiling', 'to_ascii', 'to_character', 'Length_Of', 'Abs', 'E', 'Pi',
          'Random', 'Black', 'Blue', 'Green', 'Cyan', 'Red', 'Magenta', 'Brown', 'Light_Gray', 'Dark_Gray',
          'Light_Blue', 'Light_Green', 'Light_Cyan', 'Light_Red', 'Light_Magenta', 'Yellow', 'Pink', 'Purple',
          'White', 'Filled', 'Unfilled', 'True', 'False', 'Yes', 'No', 'Random_Color', 'Random_Extended_Color',
          'Left_Button', 'Right_Button', 'Get_Max_Width', 'Get_Max_Height', 'Get_Mouse_X', 'Get_Mouse_Y',
          'Get_Window_Width', 'Get_Window_Height', 'Get_Key', 'Get_Key_String', 'Get_Font_Width',
          'Get_Font_Height', 'Load_Bitmap', 'Get_Pixel', 'Closest_Color', 'Clear_Console', 'Delay_For',
          'Redirect_Output_Append', 'Set_Precision', 'Redirect_Input', 'Redirect_Output', 'Clear_Window',
          'Play_Sound', 'Play_Sound_Background', 'Play_Sound_Background_Loop', 'Display_Number', 'Display_Text',
          'Draw_Arc', 'Close_Graph_Window', 'Freeze_Graph_Window', 'Update_Graph_Window',
          'Unfreeze_Graph_Window', 'Draw_Bitmap', 'Draw_Box', 'Draw_Circle', 'Draw_Ellipse',
          'Draw_Ellipse_Rotate', 'Draw_Line', 'Flood_Fill', 'Open_Graph_Window', 'Wait_For_Key',
          'Wait_For_Mouse_Button', 'Get_Mouse_Button', 'Set_Font_Size', 'Put_Pixel', 'Save_Graph_Window',
          'Set_Window_Title', 'Is_Number', 'Is_String', 'Is_Character', 'Is_Array', 'Is_2D_Array',
          'Mouse_Button_Pressed', 'Mouse_Button_Down', 'Key_Down', 'Mouse_Button_Released', 'Is_Open',
          'Key_Hit', 'End_Of_Input']
IDX = {n: i for i, n in enumerate(TOKENS)}
# Enum.TryParse(lexeme, ignoreCase: true): ANY identifier equal to an enum name is that token.
KEYWORD = {n.lower(): n for n in TOKENS}

# Plugin DLLs shipped with RAPTOR (plugins_powermod / stringoperations / time): name -> param count
PLUGIN_FUNCS = {'powermod': 3, 'to_integer': 1, 'to_float': 1, 'get_nth_string': 3, 'current_day': 0,
                'current_year': 0, 'current_month': 0, 'current_minute': 0, 'current_hour': 0,
                'current_second': 0, 'current_millisecond': 0, 'current_time': 0}

PROC_PARAMS = {'Clear_Console': 0, 'Delay_For': 1, 'Draw_Bitmap': 5, 'Redirect_Output_Append': 1,
               'Set_Precision': 1, 'Redirect_Input': 1, 'Redirect_Output': 1, 'Clear_Window': 1,
               'Close_Graph_Window': 0, 'Display_Number': 4, 'Display_Text': 4, 'Freeze_Graph_Window': 0,
               'Unfreeze_Graph_Window': 0, 'Update_Graph_Window': 0, 'Draw_Box': 6, 'Draw_Arc': 9,
               'Draw_Circle': 5, 'Draw_Ellipse': 6, 'Draw_Ellipse_Rotate': 7, 'Draw_Line': 5, 'Flood_Fill': 3,
               'Get_Mouse_Button': 3, 'Open_Graph_Window': 2, 'Wait_For_Key': 0, 'Wait_For_Mouse_Button': 1,
               'Put_Pixel': 3, 'Set_Font_Size': 1, 'Save_Graph_Window': 1, 'Set_Window_Title': 1,
               'Play_Sound': 1, 'Play_Sound_Background': 1, 'Play_Sound_Background_Loop': 1}


def _rng(a, b):
    lo, hi = IDX[a], IDX[b]
    return lambda k: lo <= IDX[k] <= hi


is_relation = _rng('Equal', 'Less_Equal')
is_func_token = _rng('Sin', 'Closest_Color')
is_func_id1 = _rng('Sinh', 'Abs')
is_func_id0 = _rng('E', 'Get_Font_Height')
is_func_id1or2 = _rng('Sin', 'Log')
is_func_id2or3 = _rng('Arctan', 'Arccot')
is_graph_func_id2 = _rng('Get_Pixel', 'Get_Pixel')
is_other_func_id2 = _rng('Min', 'Max')
is_func_id3 = _rng('Closest_Color', 'Closest_Color')
is_proc_token = _rng('Clear_Console', 'Set_Window_Title')
is_boolean_func = _rng('Is_Number', 'End_Of_Input')
is_boolean_reflection = _rng('Is_Number', 'Is_2D_Array')
is_boolean_func0 = _rng('Is_Open', 'End_Of_Input')
is_boolean_func1 = _rng('Mouse_Button_Pressed', 'Mouse_Button_Released')


class SyntaxErr(Exception):
    pass


class Tok:
    __slots__ = ('kind', 'start', 'finish')

    def __init__(self, kind, start, finish):
        self.kind, self.start, self.finish = kind, start, finish


class Lexer:
    def __init__(self, s):
        self.s, self.loc, self.ungot = s, 0, None

    def unget(self, t):
        if self.ungot is not None:
            raise SyntaxErr('internal: token ungotten twice')
        self.ungot = t

    def rewind(self, t):
        self.loc = t.finish + 1
        self.ungot = None

    def text(self, t):
        return self.s[t.start:t.finish + 1] if self.s else ''

    def get(self):
        if self.ungot is not None:
            t, self.ungot = self.ungot, None
            return t
        s = self.s
        c = ' '
        while ord(c) < 32 or 127 <= ord(c) <= 159 or c == ' ':
            if self.loc >= len(s):
                return Tok('End_Input', self.loc, self.loc)
            c = s[self.loc]
            self.loc += 1
        start = self.loc - 1
        L = self.loc
        nxt = s[L] if L < len(s) else ''
        if c == "'":
            if L + 1 < len(s) and s[L + 1] == "'":
                self.loc += 2
                return Tok('Character', self.loc - 3, self.loc - 1)
            raise SyntaxErr("bad character literal: single quotes are only for ONE character like 'x' "
                            "- use double quotes for text, e.g. \"hello\"")
        if c == '"':
            while self.loc < len(s):
                ch = s[self.loc]
                if ch == '"':
                    if self.loc + 1 >= len(s) or s[self.loc + 1] != '"':
                        break
                    self.loc += 1
                elif ch == '\\':
                    if self.loc + 1 < len(s) and s[self.loc + 1] == '"':
                        self.loc += 1
                self.loc += 1
            if self.loc >= len(s):
                raise SyntaxErr('missing closing " for string')
            self.loc += 1
            return Tok('String', start, self.loc - 1)
        simple = {'[': 'Left_Bracket', ']': 'Right_Bracket', ';': 'Semicolon', '+': 'Plus', '-': 'Minus',
                  ',': 'Comma', '^': 'Exponent', '%': 'Mod', '(': 'Left_Paren', ')': 'Right_Paren'}
        if c in simple:
            return Tok(simple[c], L - 1, L - 1)
        two = {'!': ('=', 'Not_Equal', None), '/': ('=', 'Not_Equal', 'Divide'), '*': ('*', 'Exponent', 'Times'),
               '&': ('&', 'And', None), '|': ('|', 'Or', None), ':': ('=', 'Colon_Equal', None),
               '>': ('=', 'Greater_Equal', 'Greater'), '<': ('=', 'Less_Equal', 'Less'),
               '=': ('=', 'Equal', 'Equal')}
        if c in two:
            follow, k2, k1 = two[c]
            if nxt == follow:
                self.loc += 1
                return Tok(k2, self.loc - 2, self.loc - 1)
            if k1 is None:
                msg = {'!': 'expected !=, found !', '&': 'expected &&, found &', '|': 'expected ||, found |',
                       ':': "': is not allowed' (assignment is written :=, e.g. x := 5)"}[c]
                raise SyntaxErr(msg)
            return Tok(k1, L - 1, L - 1)
        if ('a' <= c <= 'z') or ('A' <= c <= 'Z'):
            while self.loc < len(s) and (s[self.loc].isalnum() or s[self.loc] == '_'):
                self.loc += 1
            lex = s[start:self.loc]
            return Tok(KEYWORD.get(lex.lower(), 'Id'), start, self.loc - 1)
        if c == '.' or c.isdecimal():
            has_dec = c == '.'
            digit_after = False
            while self.loc < len(s):
                ch = s[self.loc]
                if ch == '.':
                    if has_dec:
                        raise SyntaxErr('number has two decimal points')
                    has_dec = True
                else:
                    if not ch.isdecimal():
                        break
                    if has_dec:
                        digit_after = True
                self.loc += 1
            if has_dec and not digit_after:
                if self.loc == start + 1:
                    return Tok('Dot', self.loc - 1, self.loc - 1)
                raise SyntaxErr('number may not end with decimal point')
            return Tok('Number', start, self.loc - 1)
        if c == '_':
            raise SyntaxErr("identifier can not begin with '_'")
        hint = ''
        if c in '←→':
            hint = ' (arrows are not allowed; assignment is written :=)'
        elif c in '≤≥≠':
            hint = ' (use <=, >= or !=)'
        elif c in '“”‘’':
            hint = ' (curly/smart quotes are not allowed; use plain " quotes)'
        raise SyntaxErr("found invalid character: '%s'%s" % (c, hint))


class Parser:
    def __init__(self, text, subcharts=()):
        self.lx = Lexer(text)
        self.subcharts = set(subcharts)

    def fail(self, msg):
        raise SyntaxErr(msg)

    # ---- names -------------------------------------------------------------
    def plugin_func(self, name):
        return name.lower() in PLUGIN_FUNCS

    def parse_lhs(self, ident):
        lx = self.lx
        if self.plugin_func(lx.text(ident)):
            self.fail('Invalid name, already defined as a function')
        t = lx.get()
        if t.kind == 'Left_Bracket':
            self.parse_expression()
            t = lx.get()
            if t.kind == 'Comma':
                self.parse_expression()
                t = lx.get()
            if t.kind != 'Right_Bracket':
                self.fail('missing ]')
        else:
            lx.unget(t)

    def parse_lsuffix(self):
        t = self.lx.get()
        if t.kind == 'Dot':
            self.fail("Can't use '.' in variable name")
        self.lx.unget(t)

    def parse_assignment(self):
        lx = self.lx
        t = lx.get()
        if t.kind != 'Id':
            self.fail('assignment must begin with a variable')
        self.parse_lhs(t)
        self.parse_lsuffix()
        t = lx.get()
        if t.kind not in ('Equal', 'Colon_Equal'):
            self.fail('can only set 1 variable, found: ' + t.kind)
        self.parse_expression()

    def parse_rhs(self, ident):
        lx = self.lx
        t = lx.get()
        if t.kind == 'Left_Paren':
            self.fail(lx.text(ident) + ' is not a function. (Subcharts/procedures cannot be used inside an '
                      'expression - call them from a separate Call symbol.)')
        elif t.kind == 'Left_Bracket':
            self.parse_expression()
            t = lx.get()
            if t.kind == 'Comma':
                self.parse_expression()
                t = lx.get()
            if t.kind != 'Right_Bracket':
                self.fail('missing ]')
        else:
            lx.unget(t)

    def parse_rsuffix(self):
        t = self.lx.get()
        if t.kind == 'Dot':
            self.fail("can't use '.' in variable name")
        self.lx.unget(t)

    # ---- expressions -------------------------------------------------------
    def count_params(self):
        """parse '(' already consumed by caller? no: caller consumed '(' ; returns count, leaves ')'."""
        lx = self.lx
        t = lx.get()
        if t.kind == 'Right_Paren':
            lx.unget(t)
            return 0
        lx.unget(t)
        n = 0
        while True:
            self.parse_expression()  # Parse_Output
            n += 1
            t = lx.get()
            if t.kind != 'Comma':
                lx.unget(t)
                return n

    def parse_expon(self):
        lx = self.lx
        t = lx.get()
        k = t.kind
        if k == 'Id':
            ident = t
            t = lx.get()
            name = lx.text(ident)
            if t.kind == 'Left_Paren' and self.plugin_func(name):
                n = self.count_params()
                if n != PLUGIN_FUNCS[name.lower()]:
                    self.fail('%s should have %d parameters.' % (name, PLUGIN_FUNCS[name.lower()]))
                if lx.get().kind != 'Right_Paren':
                    self.fail('missing right parenthesis')
                return
            lx.unget(t)
            if self.plugin_func(name):
                if PLUGIN_FUNCS[name.lower()] != 0:
                    self.fail('%s should have %d parameters.' % (name, PLUGIN_FUNCS[name.lower()]))
                return
            self.parse_rhs(ident)
            self.parse_rsuffix()
            return
        if k == 'New':
            self.fail("'new' is only for object-oriented mode")
        if k in ('Character', 'String', 'Number'):
            # an identifier spelled like the enum name (e.g. a variable called "number" or "string")
            # lexes as that literal kind: RAPTOR accepts the syntax but it breaks at run time.
            if lx.text(t)[:1].isalpha():
                self.fail("'%s' is a RAPTOR reserved word and cannot be used as a variable name" % lx.text(t))
            return
        if k == 'Left_Paren':
            self.parse_expression()
            if lx.get().kind != 'Right_Paren':
                self.fail('missing right parenthesis')
            return
        if is_func_id0(k):
            return
        if k == 'Minus':
            self.parse_expon()
            return
        if is_func_token(k):
            fname = lx.text(t)
            t = lx.get()
            if t.kind != 'Left_Paren':
                self.fail('missing left parenthesis after %s (it is a built-in function; if you meant a '
                          'variable, rename it)' % fname)
            n = self.count_params()
            if is_func_id1(k) or k == 'Load_Bitmap':
                if n != 1:
                    self.fail('%s should have 1 parameter, not %d' % (fname, n))
            elif is_func_id1or2(k):
                if n not in (1, 2):
                    self.fail('%s should have 1 or 2 parameters, not %d' % (fname, n))
            elif is_func_id2or3(k):
                if n not in (2, 3):
                    self.fail('%s should have 2 or 3 parameters, not %d' % (fname, n))
            elif is_other_func_id2(k) or is_graph_func_id2(k):
                if n != 2:
                    self.fail('%s should have two parameters, not %d' % (fname, n))
            elif is_func_id3(k):
                if n != 3:
                    self.fail('%s should have three parameters, not %d' % (fname, n))
            if lx.get().kind != 'Right_Paren':
                self.fail('missing right parenthesis')
            return
        word = lx.text(t)
        if k not in ('End_Input',) and word[:1].isalpha():
            self.fail("expected number or variable, found '%s' - it is a RAPTOR reserved word (%s); "
                      "rename it if it is meant to be a variable" % (word, k))
        self.fail('expected number or variable, found ' + (repr(word) if word else 'end of text'))

    def parse_mult(self):
        self.parse_expon()
        t = self.lx.get()
        if t.kind == 'Exponent':
            self.parse_mult()
        else:
            self.lx.unget(t)

    def parse_add(self):
        self.parse_mult()
        t = self.lx.get()
        if t.kind in ('Times', 'Divide', 'Mod', 'Rem'):
            self.parse_add()
        else:
            self.lx.unget(t)

    def parse_expression(self):
        self.parse_add()
        t = self.lx.get()
        if t.kind in ('Plus', 'Minus'):
            self.parse_expression()
        else:
            self.lx.unget(t)

    # ---- conditions --------------------------------------------------------
    RELS = ('Greater_Equal', 'Greater', 'Less_Equal', 'Equal', 'Not_Equal', 'Less')

    def parse_relation(self):
        lx = self.lx
        t = lx.get()
        if t.kind == 'Wait_For_Key':
            self.fail('Did you mean Key_Hit?')
        if t.kind == 'Wait_For_Mouse_Button':
            self.fail('Did you mean Mouse_Button_Pressed?')
        if is_proc_token(t.kind):
            self.fail(t.kind + ' should be in call')
        lx.unget(t)
        self.parse_expression()
        t = lx.get()
        if t.kind in self.RELS:
            first = t.kind
        else:
            got = lx.text(t) or 'end of text'
            self.fail('Expected relational operator (<,>,=,!=,<=,>=) not %r. A condition must compare '
                      'something, e.g. done = true, not just done' % got)
        self.parse_expression()
        t = lx.get()
        if t.kind in self.RELS:
            bad = {('Less', 'Less'), ('Less', 'Less_Equal'), ('Less_Equal', 'Less'), ('Less_Equal', 'Less_Equal'),
                   ('Greater', 'Greater'), ('Greater', 'Greater_Equal'), ('Greater_Equal', 'Greater'),
                   ('Greater_Equal', 'Greater_Equal')}
            if (first, t.kind) in bad:
                self.fail('chained comparison: write X<Y and Y<Z instead of X<Y<Z')
        lx.unget(t)

    def parse_boolean2(self):
        lx = self.lx
        t = lx.get()
        if t.kind == 'Not':
            t = lx.get()
        if t.kind == 'Left_Paren':
            # RAPTOR first guesses "(boolean)", and on failure rewinds and re-parses as a relation.
            try:
                self.parse_boolean_expression()
                t = lx.get()
                if t.kind != 'Right_Paren':
                    self.fail('Expected right parenthesis')
            except SyntaxErr:
                lx.rewind(t)
                lx.unget(t)
                self.parse_relation()
        elif is_boolean_func0(t.kind) or t.kind in ('True', 'False'):
            pass
        elif is_boolean_reflection(t.kind):
            if lx.get().kind != 'Left_Paren':
                self.fail('Expected left parenthesis')
            if lx.get().kind != 'Id':
                self.fail('Must have variable name here')
            if lx.get().kind != 'Right_Paren':
                self.fail('Expected right parenthesis')
        elif is_boolean_func1(t.kind):
            if lx.get().kind != 'Left_Paren':
                self.fail('Expected left parenthesis')
            self.parse_expression()
            if lx.get().kind != 'Right_Paren':
                self.fail('Expected right parenthesis')
        else:
            lx.unget(t)
            self.parse_relation()
        t = lx.get()
        if t.kind == 'And':
            self.parse_boolean2()
        else:
            lx.unget(t)

    def parse_boolean_expression(self):
        self.parse_boolean2()
        t = self.lx.get()
        if t.kind in ('Or', 'Xor'):
            self.parse_boolean_expression()
        else:
            self.lx.unget(t)

    def expect_end(self):
        t = self.lx.get()
        if t.kind != 'End_Input':
            self.fail("'%s' is unexpected" % (self.lx.text(t) or t.kind))

    # ---- statements --------------------------------------------------------
    def parse_condition(self):
        self.parse_boolean_expression()
        self.expect_end()

    def parse_output_statement(self):
        self.parse_expression()
        t = self.lx.get()
        if t.kind == 'Comma':
            self.fail("',' is unexpected - join pieces of output with +, e.g. \"Total: \" + total")
        if t.kind != 'End_Input':
            self.fail("'%s' is unexpected" % (self.lx.text(t) or t.kind))

    def parse_input_statement(self):
        t = self.lx.get()
        if t.kind != 'Id':
            word = self.lx.text(t)
            if word[:1].isalpha():
                self.fail("'%s' is a RAPTOR reserved word (%s) and cannot be a variable name; rename it"
                          % (word, t.kind))
            self.fail('Input must begin with variable')
        self.parse_lhs(t)
        self.parse_lsuffix()
        self.expect_end()

    def parse_call_statement(self):
        lx = self.lx
        t = lx.get()
        lx.unget(t)
        name = lx.text(t)
        # same order of tests as Parser.Parse_Call_Statement
        if is_proc_token(t.kind) or (name in self.subcharts and not is_func_token(t.kind)
                                     and not is_boolean_func(t.kind)):
            t = lx.get()
            user = name in self.subcharts  # Lexer.Is_Valid_Procedure: exact, case-sensitive tab name
            t2 = lx.get()
            n = 0
            if t2.kind == 'Left_Paren':
                n = self.count_params()
                if lx.get().kind != 'Right_Paren':
                    self.fail('missing )')
            else:
                lx.unget(t2)
            if not user and n != PROC_PARAMS[t.kind]:
                self.fail('%s should have %d parameters, not %d.' % (t.kind, PROC_PARAMS[t.kind], n))
        elif is_func_token(t.kind):
            self.fail(name + ' should appear in assignment (it is a function, not a procedure)')
        elif is_boolean_func(t.kind):
            self.fail(name + ' should appear in diamond (selection/loop condition)')
        else:
            self.fail("%s is not a valid procedure name (calls must name a built-in procedure or one of "
                      "this file's subcharts: %s)" % (name or 'empty', ', '.join(sorted(self.subcharts)) or 'none'))
        t = lx.get()
        if t.kind == 'Semicolon':
            t = lx.get()
        if t.kind != 'End_Input':
            self.fail("'%s' is unexpected" % (lx.text(t) or t.kind))

    def parse_assignment_statement(self):
        lx = self.lx
        t = lx.get()
        lx.unget(t)
        name = lx.text(t)
        if is_proc_token(t.kind):
            self.fail(name + ' can not be used as a variable name (built-in procedure)')
        elif is_func_token(t.kind):
            self.fail(name + ' can not be used as a variable name (built-in function/constant %s); '
                      'rename it, e.g. %s_value' % (t.kind, name))
        elif t.kind == 'Id':
            self.parse_assignment()
        elif t.kind == 'Colon_Equal':
            self.fail('Put a variable in the Set box')
        else:
            self.fail("'%s' can not begin an assignment%s" % (
                name, ' (reserved word - rename the variable)' if name[:1].isalpha() else ''))
        t = lx.get()
        if t.kind == 'Semicolon':
            t = lx.get()
        if t.kind != 'End_Input':
            self.fail("'%s' is unexpected" % (lx.text(t) or t.kind))


def _run(fn):
    try:
        fn()
        return None
    except SyntaxErr as e:
        return str(e)


def check_assignment(var, expr, subcharts=()):
    return _run(Parser(var + ':=' + expr, subcharts).parse_assignment_statement)


def check_call(text, subcharts=()):
    return _run(Parser(text, subcharts).parse_call_statement)


def check_condition(text):
    return _run(Parser(text).parse_condition)


def check_input(var_text):
    return _run(Parser(var_text).parse_input_statement)


def check_output(expr):
    return _run(Parser(expr).parse_output_statement)


def check_expression(expr):
    return _run(Parser(expr).parse_output_statement)


def reserved_word(name):
    """Return the RAPTOR token name if `name` would not lex as a plain identifier."""
    k = KEYWORD.get(name.lower())
    if k:
        return k
    if name.lower() in PLUGIN_FUNCS:
        return 'plugin function'
    return None


if __name__ == '__main__':
    import sys
    kinds = {'assign': lambda s: Parser(s).parse_assignment_statement,
             'call': lambda s: Parser(s, sys.argv[3:]).parse_call_statement,
             'cond': lambda s: Parser(s).parse_condition,
             'input': lambda s: Parser(s).parse_input_statement,
             'output': lambda s: Parser(s).parse_output_statement}
    k, text = sys.argv[1], sys.argv[2]
    err = _run(kinds[k](text))
    print('VALID' if err is None else 'INVALID: ' + err)

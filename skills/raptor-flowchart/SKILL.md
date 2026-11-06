---
name: raptor-flowchart
description: Create, check, fix or convert RAPTOR flowchart (.rap) files, e.g. Computer Basics labs; builds files that open in RAPTOR with every symbol intact.
---

# RAPTOR flowcharts (.rap files)

A `.rap` file cannot be written by hand like code. Current RAPTOR (the Avalonia version from
raptor.martincarlisle.com) saves an exact .NET DataContract XML document, and when it opens a file
it re-parses the text of every symbol and **silently blanks any symbol whose text it cannot parse**.
Almost every broken AI-made .rap comes from one of these two problems.

So **never type the XML yourself**. Write a small JSON spec and build the file with `make_rap.py`.
The script writes the XML exactly as RAPTOR's serializer does (verified byte-for-byte against a file
saved by RAPTOR) and checks every symbol with a port of RAPTOR's own lexer and parser.

## Get the tool

If `scripts/make_rap.py` and `scripts/raptor_syntax.py` sit next to this SKILL.md, use them.
Otherwise write the two files from **Appendix A** and **Appendix B** below, verbatim, into one
folder (e.g. `raptor_tool/`). Both use only the Python 3 standard library.

## Workflow

1. **Design the algorithm** for the task (inputs, outputs, loops, decisions). If the assignment
   specifies variable names, prompts, output wording, subcharts or a file name, follow it exactly.
2. **Write the spec** `spec.json` (format below).
3. **Validate**: `python3 raptor_tool/make_rap.py spec.json --check`. It prints an outline and
   every problem RAPTOR would hit. Fix the spec and repeat until it says `OK`.
4. **Build**: `python3 raptor_tool/make_rap.py spec.json -o <Name>.rap`. Use the user's naming
   convention if they have one (e.g. `Lab2_Q1_<studentID>.rap`).
5. **Deliver** the .rap file and show the outline with a short explanation of the logic.
6. Tell the user to **open it in RAPTOR, run it once, and Save**. Saving lets RAPTOR re-layout the
   chart and write its own history log into the file.

To **read or modify** an existing .rap: `make_rap.py --dump old.rap` shows the outline, and
`make_rap.py --dump old.rap --json > spec.json` gives an editable spec to rebuild from.
`--dump` also reads old binary files from classic RAPTOR 4.x, which needs `nrbf_reader.py` from the
skill zip. The builder always writes the **current XML format**, which classic RAPTOR 4.x cannot
open. If the user's own .rap files start with bytes `00 01 00 00 00 FF FF FF FF` rather than
`<MainWindowViewModel`, they are on classic RAPTOR: say so and suggest installing the current
version.

## Spec format

```json
{"subcharts": [
  {"name": "main", "body": [ ...statements... ]},
  {"name": "PrintLine", "body": [ ... ]},
  {"name": "Swap", "params": ["in out a", "in out b"], "body": [ ... ]}
]}
```
The first subchart is always the main chart (name it `main`). Any other subchart is called from a
Call symbol by its exact name, which is case-sensitive. Subcharts share all variables with main.
A subchart with `params` becomes a RAPTOR *procedure* with its own variables. Parameters are written
`"in x"`, `"out y"` or `"in out z"`. Procedures are supported but less tested, so prefer plain
subcharts unless the task asks for procedures or parameters.

Statements (each one is one JSON object, run top to bottom):

| Statement | RAPTOR symbol |
|---|---|
| `{"assign": "total", "value": "total + x"}` | Assignment `total ← total + x` |
| `{"input": "n", "prompt": "Enter a number: "}` | Input (plain-text prompt, quotes added for you) |
| `{"output": "\"Total = \" + total"}` | Output (one expression; add `"newline": false` to stay on the line) |
| `{"call": "PrintLine"}` / `{"call": "Draw_Circle(100, 100, 30, Red, Filled)"}` | Call |
| `{"if": "x > 0", "then": [...], "else": [...]}` | Selection (`else` optional) |
| `{"while": "i <= 10", "body": [...]}` | Loop, test first (converted to RAPTOR's exit test for you) |
| `{"repeat": [...], "until": "n > 0"}` | Loop, test last (body runs at least once) |
| `{"for": "i", "from": "1", "to": "n", "step": "1", "body": [...]}` | `i ← 1` + Loop that exits when `i > n`, with `i ← i + step` at the end of the body |
| `{"loop": "<EXIT condition>", "before": [...], "body": [...]}` | Raw RAPTOR loop (see the loop rule below) |

Any statement may have `"comment": "text"` (use `\n` for several lines). This attaches a RAPTOR
comment to that symbol. Example specs are in `examples/` when the skill folder is available.

## RAPTOR language rules the checker enforces

- **Loops exit when the condition is TRUE.** RAPTOR's diamond means "exit when Yes"; the body runs
  while it is false. Prefer `while`/`repeat`/`for`, which convert for you. With a raw `loop`, write
  the exit condition (`i > 10`), never the continue condition.
- **Strings use double quotes**: `"Hello"`. Single quotes are only for one character: `'x'`.
  Join with `+`: `"Area = " + area`. A comma in an output is an error.
- **Conditions must compare something**: `done = true`, not `done`. Operators: `=` `==` `!=` `/=`
  `<` `<=` `>` `>=`, plus `and` `or` `xor` `not`. There is no `<>` (auto-fixed to `!=`) and no
  chained `1 < x < 5` (write `x > 1 and x < 5`).
- **Assignment** has a variable on the left only. No `←` or `<-` inside expressions. Subcharts are
  not functions: they cannot be used inside expressions, only in Call symbols.
- **Reserved words cannot be variable names.** Any identifier equal to a RAPTOR keyword, ignoring
  case, is that keyword. Common traps: `max`, `min`, `e`, `pi`, `number`, `string`, `character`,
  `random`, `yes`, `no`, `true`, `false`, `mod`, `rem`, `and`, `or`, `not`, `log`, `abs`,
  `floor`, `ceiling`, `sqrt`, color names (`red`, `blue`, `black`, ...). Rename them, e.g.
  `max_value`, `num`.
- **Identifiers** start with a letter and use letters, digits and `_`. Numbers cannot end with a
  dot (`5.` is invalid; `.5` and `5.0` are fine).
- **Arrays** are 1-based: `a[i]`, 2-D `m[i, j]`. They are created by assigning elements, e.g. in a
  loop.
- Every variable must be assigned (or input) before it is read; this is a run-time error, not
  checked. Initialise counters and sums.
- Output is one expression per symbol. Use several Output symbols, or `"newline": false`, to build
  a line from parts.

Built-in functions, used in expressions: `sqrt abs floor ceiling sin cos tan cot arcsin arccos`
(1 arg), `log` (1 or 2), `arctan arccot` (2 or 3), `min max` (2), `sinh cosh tanh coth arcsinh
arccosh arctanh arccoth length_of to_ascii to_character` (1). Constants with no parentheses: `pi`,
`e`, `random` (0 ≤ r < 1), `true`, `false`, `yes`, `no`, colors. Operators: `+ - * /`,
`^` or `**`, `mod`, `rem` or `%`. Plugin functions that ship with RAPTOR: `To_Integer(s)`,
`To_Float(s)`, `Get_Nth_String(s, sep, n)`, `PowerMod(b, e, n)`, `Current_Year` and friends.

Built-in procedures, used in Call symbols, with their argument counts: `Clear_Console` 0,
`Set_Precision` 1, `Delay_For` 1, `Redirect_Input` 1, `Redirect_Output` 1, `Open_Graph_Window` 2,
`Close_Graph_Window` 0, `Clear_Window` 1, `Draw_Line` 5, `Draw_Box` 6, `Draw_Circle` 5,
`Draw_Ellipse` 6, `Draw_Arc` 9, `Flood_Fill` 3, `Put_Pixel` 3, `Display_Text` 4,
`Display_Number` 4, `Set_Font_Size` 1, `Set_Window_Title` 1, `Wait_For_Key` 0,
`Wait_For_Mouse_Button` 1, `Get_Mouse_Button` 3, `Freeze_Graph_Window` 0,
`Update_Graph_Window` 0, `Unfreeze_Graph_Window` 0.

## When the checker reports an error

Fix the **spec**, never the generated XML. Each message names the subchart, the statement index and
the reason, worded like RAPTOR's own messages with a hint added. Do not deliver a file until
`--check` passes. The script refuses to write one otherwise.

## Appendix A - `raptor_syntax.py` (save verbatim)

```python
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
```

## Appendix B - `make_rap.py` (save verbatim, same folder)

```python
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
```

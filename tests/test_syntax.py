import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
import raptor_syntax as rs

ok = bad = 0
cases = [
    # (fn, args, expect_valid)
    (rs.check_assignment, ('x', '5'), True),
    (rs.check_assignment, ('sum', 'sum + i * 2'), True),
    (rs.check_assignment, ('avg', '(a + b + c) / 3'), True),
    (rs.check_assignment, ('a[i]', 'a[i-1] + 1'), True),
    (rs.check_assignment, ('m[i,j]', '0'), True),
    (rs.check_assignment, ('r', 'sqrt(x) + abs(y) - floor(z) + ceiling(w)'), True),
    (rs.check_assignment, ('r', 'x mod 2 + y rem 3 + z % 4'), True),
    (rs.check_assignment, ('r', 'x ^ 2 + y ** 3'), True),
    (rs.check_assignment, ('r', 'min(a, b) + max(a, b)'), True),
    (rs.check_assignment, ('r', 'random * 100'), True),
    (rs.check_assignment, ('r', 'random()'), False),       # random takes no parentheses
    (rs.check_assignment, ('r', 'pi * r ^ 2'), True),
    (rs.check_assignment, ('s', '"Hello " + name'), True),
    (rs.check_assignment, ('c', "'x'"), True),
    (rs.check_assignment, ('n', 'length_of(s)'), True),
    (rs.check_assignment, ('t', 'true'), True),
    (rs.check_assignment, ('max', '5'), False),            # reserved
    (rs.check_assignment, ('Number', '5'), False),          # reserved
    (rs.check_assignment, ('x', 'number + 1'), False),      # reserved as value
    (rs.check_assignment, ('e', '2'), False),               # e is the constant
    (rs.check_assignment, ('x', "'hello'"), False),         # single quotes for strings
    (rs.check_assignment, ('x', 'foo(3)'), False),          # user function in expression
    (rs.check_assignment, ('x', '5.'), False),
    (rs.check_assignment, ('x', '.5'), True),
    (rs.check_assignment, ('x', 'sin(a, b)'), True),
    (rs.check_assignment, ('x', 'sqrt(a, b)'), False),
    (rs.check_assignment, ('x', 'to_integer(s)'), True),    # plugin
    (rs.check_assignment, ('x', 'x + 1;'), True),
    (rs.check_condition, ('x > 5',), True),
    (rs.check_condition, ('x >= 5 and y < 3',), True),
    (rs.check_condition, ('x = 1 or y != 2',), True),
    (rs.check_condition, ('x == 1 || y /= 2',), True),
    (rs.check_condition, ('not (x > 5)',), True),
    (rs.check_condition, ('not x > 5',), True),
    (rs.check_condition, ('(x > 5) and (y > 2)',), True),
    (rs.check_condition, ('(a + b) > c',), True),
    (rs.check_condition, ('x mod 2 = 0',), True),
    (rs.check_condition, ('done',), False),                 # needs comparison
    (rs.check_condition, ('done = true',), True),
    (rs.check_condition, ('x <> 5',), False),
    (rs.check_condition, ('1 < x < 5',), False),
    (rs.check_condition, ('key_hit',), True),
    (rs.check_condition, ('is_number(x)',), True),
    (rs.check_condition, ('x > 5 xor y > 5',), True),
    (rs.check_condition, ('answer = "yes"',), True),
    (rs.check_condition, ('answer = yes',), True),          # Yes constant
    (rs.check_output, ('"Sum = " + sum',), True),
    (rs.check_output, ('"Sum = ", sum',), False),
    (rs.check_output, ('sum',), True),
    (rs.check_output, ('"He said ""hi"""',), True),
    (rs.check_input, ('n',), True),
    (rs.check_input, ('a[i]',), True),
    (rs.check_input, ('n + 1',), False),
    (rs.check_call, ('Clear_Console',), True),
    (rs.check_call, ('clear_console',), True),
    (rs.check_call, ('Open_Graph_Window(300, 300)',), True),
    (rs.check_call, ('Open_Graph_Window(300)',), False),
    (rs.check_call, ('Draw_Circle(100, 100, 50, Red, Filled)',), True),
    (rs.check_call, ('Delay_For(0.5)',), True),
    (rs.check_call, ('PrintStars', ['PrintStars']), True),
    (rs.check_call, ('Swap(a, b)', ['Swap']), True),
    (rs.check_call, ('printstars', ['PrintStars']), False),  # case-sensitive tab names
    (rs.check_call, ('Unknown',), False),
    (rs.check_call, ('sqrt(4)',), False),
]
for fn, args, want in cases:
    err = fn(*args)
    got = err is None
    flag = 'ok ' if got == want else 'XX '
    if got == want:
        ok += 1
    else:
        bad += 1
    print(flag, fn.__name__, args, '->', 'VALID' if got else err)
print('\n%d passed, %d failed' % (ok, bad))

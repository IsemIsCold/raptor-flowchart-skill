# RAPTOR flowchart skill

Make AI-generated RAPTOR flowcharts (`.rap`) that actually open in RAPTOR with every symbol intact.

ChatGPT, Kimi and others usually get `.rap` files wrong, for two reasons:

1. **The format is exact.** Current RAPTOR saves a strict .NET DataContract XML document. Small
   differences break the file.
2. **RAPTOR silently blanks symbols it can't parse.** On open, it re-reads the text of every symbol.
   `x <- 5`, `'text'` in single quotes, `<>`, commas in outputs, bare conditions like `done`, and
   variables named `max` / `e` / `number` all get erased.

This repo fixes both. The AI writes a short JSON outline of the flowchart, and `make_rap.py` turns it
into a real `.rap`. The file is written the same way RAPTOR's own serializer writes it, and every
symbol is checked with a Python port of RAPTOR's lexer and parser first.

## Install in Claude Code

```
/plugin install raptor-flowchart --marketplace IsemIsCold/raptor-flowchart-skill
```

On Claude Code older than 2.1.275, use two steps:

```
/plugin marketplace add IsemIsCold/raptor-flowchart-skill
/plugin install raptor-flowchart@raptor-flowchart-skill
```

Then just ask, e.g. *"Make a RAPTOR flowchart that reads 10 numbers and prints their average."*

## Use it with ChatGPT, Kimi, DeepSeek...

See [FOR-OTHER-AIS.md](FOR-OTHER-AIS.md) for copy-paste prompts. Chat-only AIs (that can't run
code) write the JSON spec, and you run the script yourself.

## Run the script yourself (Python 3, no extra packages)

```
cd skills/raptor-flowchart
python scripts/make_rap.py examples/grades.json --check        # validate + show outline
python scripts/make_rap.py examples/grades.json -o grades.rap  # build
python scripts/make_rap.py --dump some_file.rap                # read an existing .rap
```

Open the result in RAPTOR, run it once, and **Save** before submitting. The spec format and all of
RAPTOR's syntax rules are in [skills/raptor-flowchart/SKILL.md](skills/raptor-flowchart/SKILL.md).

## Notes

- Writes the format of the **current RAPTOR** (Avalonia version, files start with
  `<MainWindowViewModel`). It can *read* old binary files from classic RAPTOR 4.x but not write them.
- Loops: RAPTOR exits a loop when its condition is **true**. Use `while` / `repeat` / `for` in the
  spec, which convert this for you.
- Subcharts with parameters (procedures) are supported but less tested than plain subcharts.
- `python tests/test_syntax.py` runs the syntax-checker tests.

## Layout

```
.claude-plugin/plugin.json        plugin manifest
.claude-plugin/marketplace.json   makes this repo installable as its own marketplace
skills/raptor-flowchart/          the skill: SKILL.md, scripts/, examples/
tests/                            syntax-checker tests
FOR-OTHER-AIS.md                  prompts for non-Claude AIs
```

Built from RAPTOR's public source: [carlislemc/RAPTOR_Avalonia_MVVM](https://github.com/carlislemc/RAPTOR_Avalonia_MVVM).

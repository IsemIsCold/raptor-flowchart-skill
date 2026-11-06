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

## Quick start (Python 3, no extra packages)

```
python scripts/make_rap.py examples/grades.json --check        # validate + show outline
python scripts/make_rap.py examples/grades.json -o grades.rap  # build
python scripts/make_rap.py --dump some_file.rap                # read an existing .rap
```

Open the result in RAPTOR, run it once, and **Save** before submitting.

## Using it with an AI

- **Claude:** add this folder as a skill (`SKILL.md` is the entry point).
- **ChatGPT / Kimi / DeepSeek:** see [FOR-OTHER-AIS.md](FOR-OTHER-AIS.md) for copy-paste prompts.
- **Chat-only AIs** (can't run code): ask for the JSON spec only, then run the script yourself.

The spec format and all of RAPTOR's syntax rules are in [SKILL.md](SKILL.md).

## Notes

- Writes the format of the **current RAPTOR** (Avalonia version, files start with
  `<MainWindowViewModel`). It can *read* old binary files from classic RAPTOR 4.x but not write them.
- Loops: RAPTOR exits a loop when its condition is **true**. Use `while` / `repeat` / `for` in the
  spec, which convert this for you.
- Subcharts with parameters (procedures) are supported but less tested than plain subcharts.
- `python tests/test_syntax.py` runs the syntax-checker tests.

Built from RAPTOR's public source: [carlislemc/RAPTOR_Avalonia_MVVM](https://github.com/carlislemc/RAPTOR_Avalonia_MVVM).

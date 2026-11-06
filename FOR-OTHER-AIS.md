# Using this with ChatGPT, Kimi, DeepSeek or another AI

Get the files: on GitHub press **Code → Download ZIP**, then unzip. Everything you need is in
`skills/raptor-flowchart/` (`SKILL.md`, `scripts/`, `examples/`).

**If the AI can run Python** (ChatGPT, or Kimi/DeepSeek in agent or code mode), upload the
`skills/raptor-flowchart` folder as a zip and send:

> Unzip this. Read `SKILL.md` and follow it exactly: write a JSON spec, run
> `scripts/make_rap.py --check` until it passes, then build the .rap and give me the file.
> Task: <paste the lab question here>. Save it as <Lab#_Q#_studentID>.rap.

**If the AI can only chat** (no code running), ask it for the spec only and build the file yourself
(needs Python 3 on your PC, nothing else):

> Read the attached SKILL.md. Write ONLY the JSON spec (the "Spec format" section) for this task:
> <lab question>. Follow every rule in "RAPTOR language rules". Do not write XML.

Save its answer as `spec.json` inside `skills/raptor-flowchart`, open a terminal there, and run:

```
python scripts/make_rap.py spec.json --check
python scripts/make_rap.py spec.json -o Lab1_Q1_2026xxxxxx.rap
```

If `--check` prints errors, paste them back to the AI and ask it to fix the spec.

Always open the finished file in RAPTOR, run it once, and press Save before you submit.

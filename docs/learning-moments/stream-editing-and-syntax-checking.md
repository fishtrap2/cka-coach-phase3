# Learning Moment — Stream Editing and Syntax Checking Before Commits

## What you observed

Throughout the cka-coach build sessions, before almost every `git commit`,
we ran one or more of these:

```bash
# Syntax check a Python file without running it
python3 -c "import ast; ast.parse(open('file.py').read()); print('Syntax OK')"

# Check a bash script for syntax errors without running it
bash -n scripts/testbed/providers/aws/02-aws-identity.sh && echo "Syntax OK"

# Find a specific line or pattern in a file
grep -n "some_function" src/some_file.py

# Read specific lines around a known line number
sed -n '95,115p' scripts/testbed/providers/aws/02-aws-identity.sh
```

This is not bureaucracy. Each of these serves a specific purpose.

---

## Why we do this

### 1. `python3 -c "import ast; ast.parse(...)"`  — Python syntax check

`ast.parse()` parses a Python file and raises a `SyntaxError` if the file
is not valid Python — without executing any of the code.

This catches:
- Missing colons after `if`, `def`, `class`
- Mismatched parentheses or brackets
- Incorrect indentation (Python's most common error)
- Unclosed strings

Why not just run the file? Running a Streamlit file requires a browser,
a running cluster, and all dependencies. `ast.parse()` needs none of that —
it just checks the grammar.

```bash
# Fast — no dependencies, no side effects, instant feedback
python3 -c "import ast; ast.parse(open('ui/dashboard.py').read()); print('OK')"

# Slow — requires venv, streamlit, cluster, browser
streamlit run ui/dashboard.py
```

This is the same principle as a compiler's syntax check phase — you want
to know about grammar errors before you try to run anything.

### 2. `bash -n script.sh` — Bash syntax check

`bash -n` parses a shell script and reports syntax errors without executing
any commands. The `-n` flag means "no execute" — read and check only.

This catches:
- Unclosed `if`/`fi`, `do`/`done` blocks
- Missing `;;` in `case` statements
- Unmatched quotes
- Invalid redirections

```bash
bash -n scripts/testbed/providers/aws/02-aws-identity.sh && echo "Syntax OK"
```

Critical for shell scripts because a syntax error halfway through a script
that modifies system state could leave things in a broken intermediate state.
Checking before running prevents that.

### 3. `grep -n "pattern" file` — Find before edit

Before editing a file, we use `grep -n` to find the exact line number of
the code we want to change. The `-n` flag prints line numbers.

```bash
grep -n "def ask_llm\|client = OpenAI" src/agent.py
```

Why not just open the file and search manually? In a 1,786-line file,
knowing the exact line number before making an edit means:
- The edit targets the right location
- We can verify the surrounding context with `sed -n`
- We avoid accidentally editing the wrong occurrence of a pattern

### 4. `sed -n 'START,ENDp' file` — Read specific lines

`sed -n '95,115p'` prints lines 95 to 115 of a file without printing
anything else. The `-n` flag suppresses default output, and `p` prints
the matched lines.

```bash
sed -n '95,115p' scripts/testbed/providers/aws/02-aws-identity.sh
```

This is used to:
- Verify the exact content before making an edit
- Confirm an edit landed in the right place
- Read context around a known line number without opening the whole file

---

## The broader practice — validate before commit

The pattern we follow is:

```
1. Make the change
2. Verify the syntax (ast.parse / bash -n)
3. Verify the content (grep / sed)
4. Run a minimal smoke test if possible
5. Commit
```

This is a lightweight version of a CI/CD pipeline running locally.
In a real engineering team, these checks would be automated in a pre-commit
hook or CI pipeline. We run them manually because:
- The project doesn't have a full CI pipeline yet
- It catches errors before they reach the repo
- It builds the habit of verification before commit

---

## Pre-commit hooks

A pre-commit hook is a script that runs automatically before every
`git commit`. If it exits non-zero, the commit is blocked.

A simple Python syntax pre-commit hook:

```bash
# .git/hooks/pre-commit
#!/bin/bash
for f in $(git diff --cached --name-only | grep '\.py$'); do
    python3 -c "import ast; ast.parse(open('$f').read())" || exit 1
done
```

This would catch Python syntax errors automatically on every commit
without needing to remember to run the check manually.

cka-coach does not have pre-commit hooks yet — this is a future improvement.

---

## Stream editing vs file editing

"Stream editing" refers to processing a file as a stream of text —
reading it line by line and applying transformations — rather than
opening it in an editor.

`sed` (Stream EDitor) is the classic Unix tool for this. Common uses:

```bash
# Replace a string in a file in-place
sed -i 's/SystemdCgroup = false/SystemdCgroup = true/' /etc/containerd/config.toml

# Delete lines matching a pattern
sed -i '/disabled_plugins.*cri/d' /etc/containerd/config.toml

# Print specific lines
sed -n '95,115p' file.sh
```

We use stream editing in the cka-coach scripts (e.g. fixing containerd config)
because it is:
- Scriptable — can be run non-interactively
- Precise — targets exactly what needs to change
- Auditable — the command itself documents what was changed and why
- Idempotent when written carefully — safe to run more than once

---

## ELS mapping

| Tool | ELS layer | What it checks |
|---|---|---|
| `ast.parse()` | L9 / application | Python grammar before execution |
| `bash -n` | L9 / application | Shell script grammar before execution |
| `grep -n` | L9 / application | Code navigation and verification |
| `sed -n` | L9 / application | Targeted file inspection |
| `sed -i` | L1 / L3 | System configuration via stream edit |
| Pre-commit hooks | L9 / workflow | Automated quality gate before commit |

---

## The habit

The underlying habit is: **verify before you commit, not after**.

A syntax error in a committed file:
- Breaks the build for everyone who pulls
- Creates a fix commit that pollutes the history
- May break a running service if auto-deployed

A syntax error caught locally before commit:
- Costs 2 seconds to fix
- Never reaches the repo
- Builds confidence that what you committed actually works

This is one of those practices that experienced engineers do automatically
without thinking about it — because they learned the hard way what happens
when they don't.

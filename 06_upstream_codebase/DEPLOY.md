# BuildEase — Deployment Guide (VS Code + Railway)

This is a step-by-step guide to deploy the BuildEase codebase to Railway from
VS Code on your local machine.

---

## Before you start — read this

**What this deploys today:** A working HTTP server with three endpoints
exposed — C1 (Brief Capture), C2 (Feasibility), C3a (Extreme Case Gate).
You'll see a brief-capture form, fill it in, and get feasibility output.

**What this does NOT deploy yet:** The full C1→C17 pipeline. C5–C13 are
LOCKED engine code (4,268 tests pass), but they're not yet wired into the
HTTP server. The orchestrator that runs the whole pipeline end-to-end is
S54+ work. So when you deploy, expect to see the brief-capture + feasibility
working, with the rest of the engine as importable library code behind it.

**Two paths below:**
- **Path A:** Local development first (VS Code on your machine). Strongly
  recommended — catch problems on your laptop before they cost Railway minutes.
- **Path B:** Railway deploy (after Path A works).

---

## Prerequisites

You need these installed on your machine. If any are missing, install them
first and come back here.

1. **Python 3.12 or 3.13** (`python3 --version`)
2. **Git** (`git --version`)
3. **VS Code** (you have this)
4. **Railway CLI** — install via:
   - macOS / Linux: `brew install railway` or `curl -fsSL https://railway.com/install.sh | sh`
   - Windows: `scoop install railway` or download from railway.com/cli
5. **A Railway account** — sign up at railway.com if you don't have one
6. **A GitHub account** — your existing `ramalingam38-rgb/buildease` repo

---

## Path A — Run locally in VS Code

### Step 1 — Unzip the handoff bundle

Unzip `buildemup_S53_handoff_complete.zip` somewhere on your machine. You'll
get the 10-directory bundle structure. The runnable code lives in
`06_upstream_codebase/`. Inside that you'll see:

```
06_upstream_codebase/
├── buildemup/         ← the actual Python package
├── requirements.txt   ← production dependencies
├── Procfile           ← Railway start command
├── railway.json       ← Railway config
├── runtime.txt        ← Python version pin
└── .gitignore
```

### Step 2 — Open `06_upstream_codebase/` in VS Code

```bash
cd path/to/06_upstream_codebase
code .
```

**Important:** Open `06_upstream_codebase/`, NOT the parent directory. The
`buildemup/` folder must be the package root, and the entry points must be
at the workspace root.

### Step 3 — Create a virtual environment

In VS Code's terminal (Ctrl+\` to open):

```bash
python3 -m venv .venv
```

Activate it:
- macOS / Linux: `source .venv/bin/activate`
- Windows PowerShell: `.venv\Scripts\Activate.ps1`
- Windows cmd: `.venv\Scripts\activate.bat`

You should see `(.venv)` at the start of your prompt.

### Step 4 — Install dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt   # only if you want to run tests
```

This installs `numpy` (required for C11b) plus `pytest` and `hypothesis`
for tests.

### Step 5 — Verify the test suite passes locally

```bash
cd buildemup/tests
python3 -m pytest -q
```

**Expected result:** `4268 passed, 6 skipped, 0 failed` in about 90 seconds.

If you see anything different — especially failures — **stop here** and
share the output. Don't proceed to Railway with a broken local state.

Then go back to the project root:
```bash
cd ../..
```

### Step 6 — Run the server locally

```bash
python -m buildemup.api.server
```

**Expected output:**
```
BuildemUp Component 1 + 2 + 3a listening on http://0.0.0.0:8000
  Form:                http://0.0.0.0:8000/brief_form.html
  C1 brief (POST):     http://0.0.0.0:8000/api/brief/capture
  C2 feasibility (POST): http://0.0.0.0:8000/api/feasibility/run
  Health (GET):        http://0.0.0.0:8000/health
```

You'll see a few `config validation (env=dev, non-fatal)` warnings — those
are expected in dev (RESEND_API_KEY, BUILDEMUP_DATABASE_PATH, etc. — env vars
that matter only in production).

### Step 7 — Test it in your browser

Open in a browser:
- `http://localhost:8000/brief_form.html` — the brief-capture form
- `http://localhost:8000/health` — health probe

Press `Ctrl+C` in the terminal to stop the server.

**If Path A works, you're ready for Railway.**

---

## Path B — Deploy to Railway

### Step 8 — Initialize a git repo (if not already done)

In `06_upstream_codebase/`:

```bash
git init
git add .
git commit -m "S53 handoff — 17 components LOCKED, ready for deployment"
```

### Step 9 — Push to GitHub

If you have an existing GitHub repo `ramalingam38-rgb/buildease`:

```bash
git remote add origin https://github.com/ramalingam38-rgb/buildease.git
git branch -M main
git push -u origin main
```

If the remote already exists from a prior deploy, you may need:
```bash
git remote set-url origin https://github.com/ramalingam38-rgb/buildease.git
git push -u origin main --force
```

⚠️ Be careful with `--force` if the remote has work you want to keep. Pull
first and merge if needed.

### Step 10 — Log into Railway CLI

```bash
railway login
```

This opens a browser to authenticate. Confirm and return to the terminal.

### Step 11 — Create or link a Railway project

If creating a new project:
```bash
railway init
```
Pick a name (e.g., "buildease").

If linking to an existing project (your `buildease-production` if it
already exists):
```bash
railway link
```
Pick the project from the list.

### Step 12 — Set environment variables on Railway

Railway will need a few env vars. Set them via:

```bash
railway variables set BUILDEMUP_ENV=prod
railway variables set BUILDEMUP_DATABASE_PATH=/data/buildease.db
railway variables set BUILDEMUP_ADMIN_TOKEN=<pick-a-random-32-char-string>
railway variables set BUILDEMUP_PUBLIC_URL=https://<your-app>.up.railway.app
```

Optional (only if you want email features in C3a):
```bash
railway variables set RESEND_API_KEY=<your-resend-key>
```

To generate a random admin token:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

You can also set these in the Railway dashboard under your project →
Variables.

### Step 13 — Add a persistent volume (for SQLite database)

The server uses SQLite to persist briefs, scheduler state, and C3a
events. Without a volume, every redeploy wipes the database.

In the Railway dashboard:
1. Open your service → Settings → Volumes → New Volume
2. Mount path: `/data`
3. Size: 1 GB is plenty for early use

The `BUILDEMUP_DATABASE_PATH=/data/buildease.db` you set in Step 12 will
write into this mounted volume.

### Step 14 — Deploy

```bash
railway up
```

This uploads your code and triggers a build. Watch the build logs in the
terminal or in the Railway dashboard.

**What to expect:**
- Railway detects `requirements.txt` → installs numpy
- Railway reads `Procfile` → starts `python -m buildemup.api.server`
- The `/health` endpoint is checked every few seconds during startup
- Once healthy, Railway routes public traffic to your service

### Step 15 — Get your public URL

```bash
railway domain
```

Or in the dashboard: your service → Settings → Domains → Generate Domain.

You'll get something like `buildease-production-XXXX.up.railway.app`.

### Step 16 — Smoke test the deployed service

In your browser or curl:

```bash
curl https://your-domain.up.railway.app/health
# Expected: {"ok": true, ...}

curl -o /dev/null -w "%{http_code}\n" https://your-domain.up.railway.app/brief_form.html
# Expected: 200
```

Open `https://your-domain.up.railway.app/brief_form.html` in a browser —
you should see the brief-capture form.

---

## Troubleshooting

### "Build failed: numpy installation"
Railway's nixpacks builder usually handles numpy fine. If it fails:
- Pin to an older numpy: edit `requirements.txt` → `numpy==1.26.4`
- Or add a `nixpacks.toml` forcing the right build dependencies

### "Server starts but /health returns 500"
The SQLite database hasn't initialized. The first request usually creates
the tables. Try POST to `/api/brief/capture` first; then `/health` should
pass. If not, check that `BUILDEMUP_DATABASE_PATH` points to a writable
location (your mounted `/data` volume).

### "Health check timeout"
Increase `healthcheckTimeout` in `railway.json` from 30 to 60. Or check
build logs for a Python import error preventing the server from starting.

### "Module not found: buildemup"
The `python -m buildemup.api.server` command requires `buildemup/` to be a
sibling of where you run it from. Confirm Railway is running from the
project root (where `Procfile` lives). The Procfile assumes
`06_upstream_codebase/` is the project root.

### "Tests pass locally but server can't start on Railway"
Almost always an env-var or volume issue. Check `railway logs` for the
exact error.

---

## What's not deployed (intentionally)

These exist as engine code but aren't wired into the HTTP server yet —
they'll be added in S54+ work as part of the end-to-end orchestrator:

- C5 Topology Selector
- C7 Structural Grid Engine
- C8 Corridor Designer
- C9 Room Sizer
- C10 Wet-Zone Stack Planner
- C11a Topology Mutation
- C11b NSGA-II Refinement
- C12 Vertical Alignment
- C13 Door Placement
- C14 Connection-Graph Quality
- C15 Layout Problem Finder
- C16 Dual-Drawing Renderer
- C17 Quote Comparison Engine

The HTTP layer to expose these is the next major chunk of product work
(Option B in the S53 handoff). The engine itself is 4,268-test green and
ready to be wired.

---

## What to do after deployment works

Once you have a live URL and can hit `/brief_form.html`:

1. **Fill in a real brief** through the form. Watch the network tab for
   the `/api/brief/capture` POST and `/api/feasibility/run` POST responses.
2. **Take a screenshot** of any output you find confusing or wrong.
3. **Send the trace** (you can pull it from Railway logs) to the next
   Claude for S54 work.
4. **Decide direction for S54** — Option A (pre-launch hard gates), Option
   B (orchestrator wiring to expose C5-C17), or Option C (user-facing
   surface). The S53 handoff doc recommends A or B.

---

## Summary of files added to `06_upstream_codebase/`

| File | Purpose |
|---|---|
| `requirements.txt` | Production dependencies (numpy) |
| `requirements-dev.txt` | Test dependencies (pytest, hypothesis) |
| `Procfile` | Railway start command |
| `railway.json` | Railway build + deploy config |
| `runtime.txt` | Python 3.12 pin |
| `.gitignore` | Exclude pycache, venv, db files from git |
| `DEPLOY.md` | This document |

These are the only files needed to deploy. The `buildemup/` package and
all 17 components are already in place from S53.

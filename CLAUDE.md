# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Tutor plugin (`tutor-vai`) that provides a custom Open edX theme for VAI (Veterinary Academy International). It themes both the legacy Django templates (LMS/CMS) and Micro-Frontends (MFEs) via Indigo component packages.

## Architecture

### Plugin System
`tutorvai/plugin.py` is the core — it registers with Tutor's hooks system to:
- Copy theme files to `build/openedx/themes/vai/` during `tutor config save`
- Inject dark-theme JS into Django pipeline settings via `ENV_PATCHES`
- Install Indigo npm packages into 5 MFEs (learning, learner-dashboard, profile, account, discussions) + authn
- Replace MFE footer with Indigo footer + dark theme toggle via `PLUGIN_SLOTS`
- Run `tasks/init.sh` during `tutor dev/local do init` to assign theme to Django Sites

### Theme File Flow
1. Source: `tutorvai/templates/vai/` (this repo)
2. Tutor renders → `~/Library/Application Support/tutor/env/build/openedx/themes/vai/`
3. Docker mount → `/openedx/themes/vai/` inside containers
4. `watchthemes` container detects SCSS changes → compiles CSS
5. `collectstatic` copies compiled CSS to `/openedx/staticfiles/vai/css/`

**Key implication:** Editing files in this repo does NOT auto-update the running containers. You must copy files to the tutor env directory (step 2) for changes to appear.

### SCSS Architecture
Entry point: `partials/lms/theme/_extras.scss` imports all other SCSS files at the bottom:
```
@import '../../../courseware/discover';
@import '../../../extra/header';
@import '../../../dashboard/dashboard';
...etc
```
Variables are in `_variables.scss` (primary color `#490B8A`, dark mode colors with `-d` suffix).

### Dark Mode
Cookie-based (`vai-toggle-dark`). Toggle in header sets cookie + adds `vai-dark-theme` class to `<body>`. MFE dark theme uses a MutationObserver patch (`patches/mfe-env-config-buildtime-definitions`). All dark-mode SCSS uses `body.vai-dark-theme { ... }` blocks.

### Configuration (VAI_ prefix)
Set via `tutor config save --set VAI_KEY=value`:
- `VAI_PRIMARY_COLOR` (default: `#490B8A`)
- `VAI_ENABLE_DARK_TOGGLE` (default: `True`)
- `VAI_FOOTER_NAV_LINKS` (array of `{title, url}`)
- `VAI_WELCOME_MESSAGE` (default: `"Learn. Specialize. Excel."`)

## Development Commands

```bash
# Install plugin in dev mode
pip install -e /path/to/tutor-vai-theme

# Render theme files to tutor env
tutor config save

# Start dev with theme watching
tutor dev start -d
tutor dev run --no-deps lms watchthemes  # if not already running

# After editing SCSS/templates, sync to tutor env:
cp -r tutorvai/templates/vai/* "~/Library/Application Support/tutor/env/build/openedx/themes/vai/"

# Recompile SCSS (touch triggers watchthemes)
touch "~/Library/Application Support/tutor/env/build/openedx/themes/vai/lms/static/sass/partials/lms/theme/_extras.scss"

# Collect static files
docker exec tutor_dev-lms-1 python manage.py lms collectstatic --noinput

# Assign theme to sites
tutor dev do init
```

## Deployment Workflow (CRITICAL)

After making any file changes, ALWAYS follow these steps to verify:

```bash
# 1. Render Jinja2 variables first
/Users/omerbhatti/Library/Python/3.9/bin/tutor config save

# 2. Copy ONLY modified files (NOT cp -r of entire dirs — that overwrites rendered _variables.scss/_header.scss)
TUTOR_THEME="/Users/omerbhatti/Library/Application Support/tutor/env/build/openedx/themes/vai"
SRC_THEME="/Users/omerbhatti/tutor-vai-theme/tutorvai/templates/vai"
cp "$SRC_THEME/lms/static/sass/home/_home.scss" "$TUTOR_THEME/lms/static/sass/home/_home.scss"
cp "$SRC_THEME/lms/static/sass/courseware/_discover.scss" "$TUTOR_THEME/lms/static/sass/courseware/_discover.scss"
cp "$SRC_THEME/lms/static/sass/partials/lms/theme/_extras.scss" "$TUTOR_THEME/lms/static/sass/partials/lms/theme/_extras.scss"
cp "$SRC_THEME/lms/templates/index.html" "$TUTOR_THEME/lms/templates/index.html"
cp "$SRC_THEME/lms/templates/course.html" "$TUTOR_THEME/lms/templates/course.html"
cp "$SRC_THEME/lms/templates/discovery/course_card.underscore" "$TUTOR_THEME/lms/templates/discovery/course_card.underscore"

# 3. CRITICAL: Touch _extras.scss INSIDE CONTAINER to force full recompile
# Watchthemes caches old compiled CSS and won't pick up new styles from imported partials!
docker exec tutor_dev-lms-1 touch /openedx/themes/vai/lms/static/sass/partials/lms/theme/_extras.scss

# 4. Wait for watchthemes to recompile (~10 seconds)
sleep 10 && docker logs tutor_dev-watchthemes-run-b5a39ad9317c --tail 5

# 5. Verify new styles are in compiled CSS (replace YOUR_SELECTOR)
docker exec tutor_dev-lms-1 grep -c "YOUR_SELECTOR" /openedx/themes/vai/lms/static/css/lms-main-v1.css

# 6. Run collectstatic
docker exec tutor_dev-lms-1 python manage.py lms collectstatic --noinput

# 7. Hard refresh the browser (Cmd+Shift+R)
```

### WARNING: `tutor config save` Overwrites Theme Files
Running `tutor config save` re-renders the entire `env/build/` directory from the plugin source (`tutorvai/templates/`). This is needed to process Jinja2 variables (`{{ VAI_WELCOME_MESSAGE }}`, `{% if VAI_ENABLE_DARK_TOGGLE %}`, etc.).

**However**, it will overwrite ANY manual edits in `env/build/`. After running `tutor config save`, you MUST re-copy ALL modified source files from this repo to the tutor env. Always copy ALL files, not just the latest changes — otherwise previously modified files will revert.

### Tutor Binary Path
The `tutor` command is not in PATH by default. Use the full path:
```bash
/Users/omerbhatti/Library/Python/3.9/bin/tutor config save
```

### Watchthemes Container
The watchthemes container name is `tutor_dev-watchthemes-run-b5a39ad9317c`. Check its logs to confirm SCSS compilation succeeded before running collectstatic.

## Important Patterns

- **Course cards** use horizontal flex layout (image 40% left, content 60% right) defined in `courseware/_discover.scss`. Homepage cards are single-column centered via `_extras.scss`.
- **Templates**: `course.html` (Mako) = homepage cards, `course_card.underscore` (Backbone) = discover page cards. Both need parallel changes.
- **Dark theme SCSS** always lives in `body.vai-dark-theme { }` blocks at the bottom of each SCSS file, mirroring the light-mode selectors with `-d` suffix variables.
- **Payload CMS nested arrays limitation**: Never use nested arrays (array inside array) in Payload CMS 3.0 beta — use flattened top-level arrays instead.

## MFE Styling via plugin.py

### Figma Style Guide (ALWAYS follow for buttons/typography)
Design file: `figma.com/design/nzEyLZ2r98goJZN9woS1dt/VAI-Design--Copy-`

**Primary button** (node `630:13557`): `bg: #490B8A`, white text, `border-radius: 100px`, `height: 50px`, `px: 24px`, Garet Bold 16px. Hover: `#2B0157`. Disabled: `bg: #E9E7EC`, `color: #A5A0AD`. Ghosted: white bg, `border: 1px solid #490B8A`, purple text.

**Secondary button** (node `630:13570`): white bg, `border: 1px solid #490B8A`, `color: #490B8A`. Hover: `bg: #F5ECFF`. Disabled: `bg: #F8F8F8`, `color: #A5A0AD`.

**Font**: Garet (Book 400, Regular 500, Bold 700, ExtraBold 800) from LMS static. Fallback: Poppins via Google Fonts CDN.

### How MFE patches work
Each MFE gets a `mfe-env-config-buildtime-definitions` patch in `plugin.py`, gated by `if (process.env.APP_ID === '<mfe-name>')`. Contains injected CSS + JS (logo swap, MutationObserver for React re-renders).

### Styled MFEs
| MFE | Port | Dev file |
|-----|------|----------|
| authn | 1999 | `/tmp/authn-index.html` |
| learner-dashboard | 1996 | (built into image) |
| profile | 1995 | `/tmp/profile-index.html` |

### Dev iteration (any MFE, no rebuild needed)
```bash
# 1. Copy current index.html from container
docker cp tutor_dev-mfe-1:/openedx/dist/<mfe>/index.html /tmp/<mfe>-index.html

# 2. Add <script> block with CSS+JS before </body> in /tmp/<mfe>-index.html

# 3. Restart MFE (flush Caddy cache) + inject
/Users/omerbhatti/Library/Python/3.9/bin/tutor dev restart mfe && sleep 5 && docker cp /tmp/<mfe>-index.html tutor_dev-mfe-1:/openedx/dist/<mfe>/index.html

# 4. Hard refresh browser
```

### CSS join escaping (CRITICAL)
- **In `/tmp/*-index.html`** (raw HTML): use `].join(' ')` — double-backslash `\\n` in HTML produces literal `\n` which CSS misparses as escape, prepending `n` to every selector after the first
- **In `plugin.py`** (Python triple-quoted string): use `].join('\\n')` — Python `\\n` → HTML `\n` → JS newline (correct)

### Production deployment (permanent)
```bash
/Users/omerbhatti/Library/Python/3.9/bin/tutor images build mfe
/Users/omerbhatti/Library/Python/3.9/bin/tutor local start -d mfe
```

### CORS fonts in dev
Garet fonts at `local.openedx.io:8000` are blocked from `apps.local.openedx.io:<port>`. Falls back to Poppins. Not an issue in production (same-origin via Caddy).

## Dependencies
- Tutor 18.0–20.x
- Tutor-MFE 18.0–20.x
- `@edly-io/indigo-brand-openedx@^2.2.2` (MFE branding)
- `@edly-io/indigo-frontend-component-footer@^3.0.0` (MFE footer)
- Garet font family (OFL licensed, in `lms/static/fonts/`)

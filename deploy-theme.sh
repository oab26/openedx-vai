#!/bin/bash
# VAI Theme Deploy Script
# Deploys theme changes from the repo to the local Tutor dev environment.
# Usage: ./deploy-theme.sh

set -e

TUTOR_BIN="/Users/omerbhatti/Library/Python/3.9/bin/tutor"
TUTOR_ROOT="$HOME/Library/Application Support/tutor"
THEME_SRC="$(cd "$(dirname "$0")/tutorvai/templates/vai" && pwd)"
THEME_DST="$TUTOR_ROOT/env/build/openedx/themes/vai"
LMS_CONTAINER="tutor_dev-lms-1"

# Files with Jinja2 templates — these are correctly rendered by `tutor config save`
# and must NOT be overwritten by raw source copies.
JINJA2_FILES=(
    "lms/static/sass/partials/lms/theme/_variables.scss"
    "cms/static/sass/partials/cms/theme/_variables.scss"
    "lms/static/sass/extra/_header.scss"

    "lms/templates/index_overlay.html"
    "lms/static/js/dark-theme.js"
    "tasks/init.sh"
)

echo "==> Step 1/5: Running tutor config save (renders Jinja2 vars)..."
"$TUTOR_BIN" config save > /dev/null 2>&1

echo "==> Step 2/5: Copying source files to tutor env (skipping Jinja2 files)..."
EXCLUDE_ARGS=()
for f in "${JINJA2_FILES[@]}"; do
    EXCLUDE_ARGS+=(! -path "./$f")
done
cd "$THEME_SRC"
find . -type f "${EXCLUDE_ARGS[@]}" -exec cp {} "$THEME_DST/{}" \;

echo "==> Step 3/5: Touching _extras.scss to force recompile..."
docker exec "$LMS_CONTAINER" touch /openedx/themes/vai/lms/static/sass/partials/lms/theme/_extras.scss

echo "==> Step 4/5: Waiting for watchthemes recompilation (~12s)..."
sleep 12

echo "==> Step 5/6: Running collectstatic..."
docker exec "$LMS_CONTAINER" python manage.py lms collectstatic --noinput > /dev/null 2>&1

echo "==> Step 6/6: Restarting LMS to clear Mako template cache..."
docker restart "$LMS_CONTAINER" > /dev/null 2>&1
sleep 15

echo ""
echo "Done! Hard refresh your browser to see changes."

from __future__ import annotations

import os
import typing as t

import importlib_resources
from tutor import hooks
from tutor.__about__ import __version_suffix__
# PLUGIN_SLOTS not used — Indigo disabled, VAI handles styling via Dockerfile patches

from .__about__ import __version__

if __version_suffix__:
    __version__ += "-" + __version_suffix__


################# Configuration
config: t.Dict[str, t.Dict[str, t.Any]] = {
    "defaults": {
        "VERSION": __version__,
        "WELCOME_MESSAGE": "Learn. Specialize. Excel.",
        "PRIMARY_COLOR": "#490B8A",
        "ENABLE_DARK_TOGGLE": True,
        "MARKETING_SITE_URL": "http://localhost:3000",
        "FOOTER_NAV_LINKS": [
            {"title": "About Us", "url": "/about"},
            {"title": "Programs", "url": "/programs"},
            {"title": "Terms of Service", "url": "/tos"},
            {"title": "Privacy Policy", "url": "/privacy"},
            {"title": "Help", "url": "/help"},
            {"title": "Contact Us", "url": "/contact"},
        ],
    },
    "unique": {},
    "overrides": {
        "PLATFORM_NAME": "VAI - Veterinary Academy International",
    },
}

# Theme templates
hooks.Filters.ENV_TEMPLATE_ROOTS.add_item(
    str(importlib_resources.files("tutorvai") / "templates")
)
hooks.Filters.ENV_TEMPLATE_TARGETS.add_items(
    [
        ("vai", "build/openedx/themes"),
    ],
)

# Force the rendering of scss files, even though they are included in a "partials" directory
hooks.Filters.ENV_PATTERNS_INCLUDE.add_items(
    [
        r"vai/lms/static/sass/partials/lms/theme/",
        r"vai/cms/static/sass/partials/cms/theme/",
    ]
)


# init script: set theme automatically
with open(
    os.path.join(
        str(importlib_resources.files("tutorvai") / "templates"),
        "vai",
        "tasks",
        "init.sh",
    ),
    encoding="utf-8",
) as task_file:
    hooks.Filters.CLI_DO_INIT_TASKS.add_item(("lms", task_file.read()))


# Load all configuration entries
hooks.Filters.CONFIG_DEFAULTS.add_items(
    [(f"VAI_{key}", value) for key, value in config["defaults"].items()]
)
hooks.Filters.CONFIG_UNIQUE.add_items(
    [(f"VAI_{key}", value) for key, value in config["unique"].items()]
)
hooks.Filters.CONFIG_OVERRIDES.add_items(list(config["overrides"].items()))

# Allow marketing site to receive redirects from Open edX after registration/login
hooks.Filters.ENV_PATCHES.add_item(
    (
        "openedx-lms-common-settings",
        'LOGIN_REDIRECT_WHITELIST.append("{{ VAI_MARKETING_SITE_URL.replace("https://", "").replace("http://", "") }}")',
    )
)

# Email sender configuration (Resend SMTP)
hooks.Filters.ENV_PATCHES.add_item(
    (
        "openedx-lms-common-settings",
        """
DEFAULT_FROM_EMAIL = "VAI - Veterinary Academy International <noreply@updates.bytecrew.net>"
SERVER_EMAIL = "noreply@updates.bytecrew.net"
""",
    )
)

# Enable bulk enrollment API for ecommerce
hooks.Filters.ENV_PATCHES.add_item(
    (
        "openedx-lms-common-settings",
        'FEATURES["ENABLE_BULK_ENROLLMENT_VIEW"] = True',
    )
)

# Redirect LMS course discovery and homepage to marketing site
hooks.Filters.ENV_PATCHES.add_item(
    (
        "openedx-lms-common-settings",
        """
MKTG_URL_LINK_MAP = {
    "ROOT": "{{ VAI_MARKETING_SITE_URL }}",
    "COURSES": "{{ VAI_MARKETING_SITE_URL }}/courses",
    "ABOUT": "{{ VAI_MARKETING_SITE_URL }}/about",
    "CONTACT": "{{ VAI_MARKETING_SITE_URL }}/contact",
}
MKTG_URLS = {"ROOT": "{{ VAI_MARKETING_SITE_URL }}"}
""",
    )
)

# Allow MFEs to load Garet fonts from LMS (cross-origin)
hooks.Filters.ENV_PATCHES.add_item(
    (
        "caddyfile-lms",
        """
        header /static/vai/fonts/* Access-Control-Allow-Origin *
""",
    )
)

# Install openedx-atlas in the MFE base image (needed for pull_translations)
hooks.Filters.ENV_PATCHES.add_item(
    (
        "mfe-dockerfile-base",
        "RUN apt update && apt install -y python3-pip && pip3 install openedx-atlas",
    )
)

# Fix fedx-scripts missing for broken MFEs (learner-record, communications, ora-grading)
# These MFEs fail npm clean-install due to cached/corrupt node_modules.
# Force reinstall of frontend-build which provides fedx-scripts.
for _broken_mfe in ["learner-record", "communications", "ora-grading"]:
    hooks.Filters.ENV_PATCHES.add_item(
        (
            f"mfe-dockerfile-post-npm-install-{_broken_mfe}",
            "RUN npm ls @openedx/frontend-build 2>/dev/null || npm ls @edx/frontend-build 2>/dev/null || npm install @openedx/frontend-build --no-save",
        )
    )

# MFEs that are styled using Indigo packages (Phase 1: reuse Indigo MFE npm packages)
vai_styled_mfes = [
    "learning",
    "learner-dashboard",
    "profile",
    "account",
    "discussions",
]


# Install Indigo npm packages for styled MFEs (header, footer, brand)
for mfe in vai_styled_mfes:
    hooks.Filters.ENV_PATCHES.add_item(
        (
            f"mfe-dockerfile-post-npm-install-{mfe}",
            """
RUN npm install @edly-io/indigo-frontend-component-footer@^3.0.0
RUN npm install '@edx/frontend-component-header@npm:@edly-io/indigo-frontend-component-header@^4.0.0'
RUN npm install '@edx/brand@npm:@edly-io/indigo-brand-openedx@^2.2.2'
""",
        ),
    )


hooks.Filters.ENV_PATCHES.add_item(
    (
        "mfe-dockerfile-post-npm-install-authn",
        "RUN npm install '@edx/brand@npm:@edly-io/indigo-brand-openedx@^2.2.2'",
    )
)

# ─── VAI MFE Styling via Dockerfile patches ───
# Uses mfe-dockerfile-post-npm-build-{mfe} to inject <style>/<script> into
# the built index.html — same as docker cp but permanent in the Docker image.
_patches_dir = str(importlib_resources.files("tutorvai") / "patches")


def _load_patch(filename: str) -> str:
    filepath = os.path.join(_patches_dir, filename)
    if os.path.exists(filepath):
        with open(filepath, encoding="utf-8") as f:
            return f.read()
    return ""


def _make_inject_script(mfe_name: str, patch_filename: str, tag: str = "script") -> str:
    """Generate a Dockerfile RUN command that injects a file into index.html."""
    return f"""
RUN node -e "
const fs = require('fs');
const content = fs.readFileSync('/openedx/app/vai-inject.txt', 'utf8');
let html = fs.readFileSync('/openedx/app/dist/index.html', 'utf8');
html = html.replace('</head>', '<{tag}>' + content + '</{tag}></head>');
fs.writeFileSync('/openedx/app/dist/index.html', html);
"
"""


# Set VAI logo for all MFEs via MFE_CONFIG
hooks.Filters.ENV_PATCHES.add_item(
    (
        "mfe-lms-common-settings",
        """
MFE_CONFIG["LOGO_URL"] = "https://{{ LMS_HOST }}/static/vai/images/logo.svg"
MFE_CONFIG["LOGO_TRADEMARK_URL"] = "https://{{ LMS_HOST }}/static/vai/images/logo.svg"
MFE_CONFIG["LOGO_WHITE_URL"] = "https://{{ LMS_HOST }}/static/vai/images/logo-white.svg"
""",
    )
)


# ─── Per-MFE CSS/JS injection via Dockerfile post-build patches ───
# Each MFE gets: (1) write patch file during install, (2) inject into index.html after build

_vai_mfe_patches = {
    "learner-dashboard": ("vai-dashboard-css.txt", "style"),
    "authn": ("vai-authn-script.txt", "script"),
    "learning": ("vai-learning-script.txt", "script"),
    "discussions": ("vai-discussions-script.txt", "script"),
    "authoring": ("vai-authoring-script.txt", "script"),
    "profile": ("vai-profile-css.txt", "style"),
    "account": ("vai-account-css.txt", "style"),
}

for _mfe_name, (_patch_file, _tag) in _vai_mfe_patches.items():
    _content = _load_patch(_patch_file)
    if _content:
        _b64 = __import__("base64").b64encode(_content.encode()).decode()
        hooks.Filters.ENV_PATCHES.add_item(
            (
                f"mfe-dockerfile-post-npm-install-{_mfe_name}",
                f"RUN echo '{_b64}' | base64 -d > /openedx/app/vai-inject.txt"
                " && sed -i 's|__LMS_FONTS_BASE__|{% if ENABLE_HTTPS %}https://{{ LMS_HOST }}{% else %}http://{{ LMS_HOST }}{% endif %}/static/vai/fonts/|g' /openedx/app/vai-inject.txt",
            )
        )
        hooks.Filters.ENV_PATCHES.add_item(
            (
                f"mfe-dockerfile-post-npm-build-{_mfe_name}",
                f"""RUN node -e "var fs=require('fs'),c=fs.readFileSync('/openedx/app/vai-inject.txt','utf8'),h=fs.readFileSync('/openedx/app/dist/index.html','utf8');h=h.replace('</body>','<{_tag}>'+c+'</{_tag}></body>');fs.writeFileSync('/openedx/app/dist/index.html',h);" """,
            )
        )



# Include js file in lms main.html, main_django.html, and certificate.html
# Include js file in lms main.html, main_django.html, and certificate.html
hooks.Filters.ENV_PATCHES.add_items(
    [
        # for production
        (
            "openedx-common-assets-settings",
            """
javascript_files = ['base_application', 'application', 'certificates_wv']
dark_theme_filepath = ['vai/js/dark-theme.js']

for filename in javascript_files:
    if filename in PIPELINE['JAVASCRIPT']:
        PIPELINE['JAVASCRIPT'][filename]['source_filenames'] += dark_theme_filepath
""",
        ),
        # for development
        (
            "openedx-lms-development-settings",
            """
javascript_files = ['base_application', 'application', 'certificates_wv']
dark_theme_filepath = ['vai/js/dark-theme.js']

for filename in javascript_files:
    if filename in PIPELINE['JAVASCRIPT']:
        PIPELINE['JAVASCRIPT'][filename]['source_filenames'] += dark_theme_filepath

MFE_CONFIG['INDIGO_ENABLE_DARK_TOGGLE'] = {{ VAI_ENABLE_DARK_TOGGLE }}
MFE_CONFIG['INDIGO_FOOTER_NAV_LINKS'] = {{ VAI_FOOTER_NAV_LINKS }}
""",
        ),
        (
            "openedx-lms-production-settings",
            """
MFE_CONFIG['INDIGO_ENABLE_DARK_TOGGLE'] = {{ VAI_ENABLE_DARK_TOGGLE }}
MFE_CONFIG['INDIGO_FOOTER_NAV_LINKS'] = {{ VAI_FOOTER_NAV_LINKS }}
""",
        ),
    ]
)


# No PLUGIN_SLOTS needed — VAI CSS hides default footer and handles all styling
# Indigo plugin is disabled; all MFE theming is done via post-build CSS/JS injection

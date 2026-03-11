from __future__ import annotations

import os
import typing as t
from glob import glob

import importlib_resources
from tutor import hooks
from tutor.__about__ import __version_suffix__
from tutormfe.hooks import PLUGIN_SLOTS

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
        ("vai/env.config.jsx", "plugins/mfe/build/mfe"),
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


# MFEs that are styled using Indigo packages (Phase 1: reuse Indigo MFE npm packages)
vai_styled_mfes = [
    "learning",
    "learner-dashboard",
    "profile",
    "account",
    "discussions",
]


for mfe in vai_styled_mfes:
    hooks.Filters.ENV_PATCHES.add_items(
        [
            (
                f"mfe-dockerfile-post-npm-install-{mfe}",
                """
RUN npm install @edly-io/indigo-frontend-component-footer@^3.0.0
RUN npm install '@edx/frontend-component-header@npm:@edly-io/indigo-frontend-component-header@^4.0.0'
RUN npm install '@edx/brand@npm:@edly-io/indigo-brand-openedx@^2.2.2'

""",
            ),
            (
                f"mfe-env-config-runtime-definitions-{mfe}",
                """
const { default: IndigoFooter } = await import('@edly-io/indigo-frontend-component-footer');
""",
            ),
        ]
    )


hooks.Filters.ENV_PATCHES.add_item(
    (
        "mfe-dockerfile-post-npm-install-authn",
        "RUN npm install '@edx/brand@npm:@edly-io/indigo-brand-openedx@^2.2.2'",
    )
)

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


# Apply patches from tutor-vai
for path in glob(
    os.path.join(
        str(importlib_resources.files("tutorvai") / "patches"),
        "*",
    )
):
    with open(path, encoding="utf-8") as patch_file:
        hooks.Filters.ENV_PATCHES.add_item((os.path.basename(path), patch_file.read()))


for mfe in vai_styled_mfes:
    PLUGIN_SLOTS.add_item(
        (
            mfe,
            "footer_slot",
            """
            {
                op: PLUGIN_OPERATIONS.Hide,
                widgetId: 'default_contents',
            },
            {
                op: PLUGIN_OPERATIONS.Insert,
                widget: {
                    id: 'default_contents',
                    type: DIRECT_PLUGIN,
                    priority: 1,
                    RenderWidget: <IndigoFooter />,
                },
            },
            {
                op: PLUGIN_OPERATIONS.Insert,
                widget: {
                    id: 'read_theme_cookie',
                    type: DIRECT_PLUGIN,
                    priority: 2,
                    RenderWidget: AddDarkTheme,
                },
            },
  """,
        ),
    )

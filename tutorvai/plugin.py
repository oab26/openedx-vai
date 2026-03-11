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


# VAI Authn MFE styling — Register/Sign-in page overrides
# Uses mfe-env-config-buildtime-definitions (module-level) because the authn MFE
# does not have @openedx/frontend-plugin-framework, so runtime-definitions patches
# (inside the try block) never execute.
hooks.Filters.ENV_PATCHES.add_item(
    (
        "mfe-env-config-buildtime-definitions",
        """
if (process.env.APP_ID === 'authn') {
  (function() {
    var lmsBase = '{% if ENABLE_HTTPS %}https://{{ LMS_HOST }}{% else %}http://{{ LMS_HOST }}:8000{% endif %}';
    var vaiLogoBase64 = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNzAiIGhlaWdodD0iNDUiIHZpZXdCb3g9IjAgMCA3MCA0NSIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGcgY2xpcC1wYXRoPSJ1cmwoI2NsaXAwXzIwMDFfMTYxOSkiPgo8cGF0aCBkPSJNMCAxMi4wODM4QzQuMDk3NzIgMTIuMzExMiA5LjA0NDY0IDEyLjg5OTMgMTEuODYyMyAxNi4yNDZDMTQuNDA1MiAxOS4yNjY2IDE2LjU0ODUgMjcuMTgzMyAxOS44MDQ5IDI4LjU5MTZDMjEuNTkwNyAyOS4zNjQ3IDIzLjY0MDMgMjguOTA1MiAyNS4yMjYzIDI3Ljg2N0MyNS4zMzU2IDI3Ljc5NjUgMjUuNDc5MiAyNy44MDEyIDI1LjQzNzEgMjcuNjA2N0MyMy41NDUxIDI4LjEzMDUgMjEuMTgzMyAyNy4xNDg4IDIwLjE5NTEgMjUuNDU1QzE5LjAwMjUgMjMuNDExNSAxOS42MTYgMjEuNjcwNyAyMC40OTk1IDE5LjY4NTNDMjIuMTAxMiAxNi4wODE0IDI0LjAxODEgMTIuMjQzOCAyNS43ODk5IDguNzA1NzRDMjguODEyIDIuNjc0MTEgMzIuNzMzNCAwLjMwMTI5OSAzOS40ODAyIDAuMDc3MDM0N0MzOS42ODk0IDAuMDcwNzYxNSAzOS44ODQ1IC0wLjExNTg2NCA0MC4wMzQzIDAuMTE5Mzc4TDIwLjM1MjggNDIuOTUyNEMxOS4wMDg3IDQ1LjMwNjQgMTUuNDMwOCA0NS4wMjcyIDE0LjE1MzkgNDIuNzYxTDAgMTIuMDgzOFoiIGZpbGw9IndoaXRlIi8+CjxwYXRoIGQ9Ik02MS44MDQ3IDMxLjEyMjZINTUuOTE0OUw1My43MjQ4IDI1LjkwNDlMNDIuNzM1MSAyNS44ODYxTDQwLjYzNCAzMS4xMjI2SDM0Ljc4NjNMMzQuNjk0MiAzMC45NDY5TDQ0Ljk5NTUgNS4xODc4OEw0NS4yODEyIDUuMDQ1MTdDNDcuMjEwNiA1LjIzMzM2IDQ5LjU2IDQuODEzMDYgNTEuNDM3OSA1LjA0NTE3QzUxLjUzMTYgNS4wNTYxNCA1MS42MjgzIDUuMDQwNDYgNTEuNjkwOCA1LjEzNDU2TDYxLjgwNDcgMzEuMTIyNlpNNTEuOTAzMSAyMC44MzE1TDQ4LjQwMTcgMTEuMDU0OEw0NC41NjE1IDIwLjgzMTVINTEuOTAzMVoiIGZpbGw9IndoaXRlIi8+CjxwYXRoIGQ9Ik02OS45OTk5IDMxLjAzNzlDNjguNzkxNyAzMS4wNTk5IDY3LjU3NzIgMzEuMDA5NyA2Ni4zNjg5IDMxLjAzNDhDNjYuMDE5MyAzMS4wNDI2IDY0LjM5NzMgMzEuMjgyNiA2NC4yMzE5IDMxLjAzOTVDNjQuMTgwNCAzMC45NzgzIDY0LjI4MTggMzAuOTMxMyA2NC4yODE4IDMwLjkwOTNWNS4wNTE0NEg2OS44NzM1TDcwLjAwMTUgNS4xODAwNFYzMS4wMzc5SDY5Ljk5OTlaIiBmaWxsPSJ3aGl0ZSIvPgo8L2c+CjxkZWZzPgo8Y2xpcFBhdGggaWQ9ImNsaXAwXzIwMDFfMTYxOSI+CjxyZWN0IHdpZHRoPSI3MCIgaGVpZ2h0PSI0NC41OTI2IiBmaWxsPSJ3aGl0ZSIvPgo8L2NsaXBQYXRoPgo8L2RlZnM+Cjwvc3ZnPgo=';

    var fontLink = document.createElement('link');
    fontLink.href = 'https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap';
    fontLink.rel = 'stylesheet';
    document.head.appendChild(fontLink);

    var style = document.createElement('style');
    style.id = 'vai-authn-styles';
    style.textContent = [
      "@font-face { font-family: 'Garet'; src: url('" + lmsBase + "/static/vai/fonts/Garet-ExtraBold.otf') format('opentype'); font-weight: 800; font-style: normal; font-display: swap; }",
      "@font-face { font-family: 'Garet'; src: url('" + lmsBase + "/static/vai/fonts/Garet-Book.otf') format('opentype'); font-weight: 400; font-style: normal; font-display: swap; }",
      "body { font-family: 'Poppins', sans-serif !important; }",
      ".bg-primary-400 { background-color: #490B8A !important; }",
      ".large-screen-svg-primary, .medium-screen-svg-primary { display: none !important; }",
      ".extra-large-screen-top-stripe { display: none !important; }",
      ".large-yellow-line, .medium-yellow-line, .small-yellow-line { display: none !important; }",
      ".layout > .w-50 > .col-md-3 { display: none !important; }",
      ".layout > .w-50 > .col-md-9 { flex: 0 0 100% !important; max-width: 100% !important; }",
      ".layout > .w-50:first-child { display: flex !important; align-items: center !important; justify-content: center !important; }",
      ".layout > .w-50:first-child .col-md-9 { display: flex !important; flex-direction: column !important; justify-content: center !important; min-height: 100vh !important; padding: 60px 90px !important; }",
      "img.logo { width: 70px !important; height: auto !important; position: relative !important; top: auto !important; left: auto !important; margin-bottom: 8px !important; }",
      ".logo.position-absolute { position: relative !important; }",
      "#vai-brand-text { color: white; font-family: 'Poppins', sans-serif; font-size: 11px; font-weight: 500; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 40px; opacity: 0.9; }",
      ".layout .w-50 h1, .layout .w-50 .display-1 { font-family: 'Garet', 'Poppins', sans-serif !important; font-weight: 800 !important; font-size: 48px !important; line-height: 64px !important; color: white !important; max-width: 500px !important; margin: 0 !important; }",
      ".text-accent-a { display: none !important; }",
      ".vai-green-underline { position: relative; display: inline; }",
      ".vai-green-underline::after { content: ''; position: absolute; bottom: 2px; left: 0; width: 100%; height: 6px; background: #2DBE6C; border-radius: 3px; z-index: -1; }",
      "@media (min-width: 768px) and (max-width: 1199px) {",
      "  .w-100.p-0.mb-3.d-flex > .col-md-10.bg-primary-400 { background-color: #490B8A !important; }",
      "  .w-100.p-0.mb-3.d-flex > .col-md-2 { display: none !important; }",
      "  .w-100.p-0.mb-3.d-flex > .col-md-10 { flex: 0 0 100% !important; max-width: 100% !important; }",
      "  .medium-screen-top-stripe { display: none !important; }",
      "}",
      "@media (max-width: 767px) {",
      "  span.bg-primary-400 { background-color: #490B8A !important; }",
      "  .small-screen-top-stripe { display: none !important; }",
      "}",
      ".content { max-width: 50% !important; padding: 0 2rem !important; }",
      ".mw-xs { max-width: 486px !important; margin: 0 auto !important; }",
      "#controlled-tab { border-bottom: 1px solid #dedede !important; margin-bottom: 24px !important; }",
      "#controlled-tab .nav-link { font-family: 'Garet', 'Poppins', sans-serif !important; font-size: 16px !important; font-weight: 700 !important; color: #101114 !important; border: none !important; border-bottom: 2px solid transparent !important; padding: 10px 22px !important; background: transparent !important; }",
      "#controlled-tab .nav-link.active { border-bottom-color: #101114 !important; color: #101114 !important; }",
      "#controlled-tab .nav-link:hover { border-bottom-color: #999 !important; }",
      ".pgn__form-group { margin-bottom: 16px !important; }",
      ".form-control, .pgn__form-control-floating-label-content { border-radius: 10px !important; }",
      ".form-control { height: 55px !important; border: 1px solid #dfe1e7 !important; font-family: 'Poppins', sans-serif !important; font-size: 14px !important; padding-left: 16px !important; }",
      ".form-control:focus { border-color: #490B8A !important; box-shadow: 0 0 0 1px #490B8A !important; }",
      ".pgn__form-label { font-family: 'Poppins', sans-serif !important; font-weight: 500 !important; font-size: 14px !important; color: #271b11 !important; }",
      "select.form-control { height: 55px !important; border-radius: 10px !important; }",
      ".btn-brand { background-color: #490B8A !important; border-color: #490B8A !important; border-radius: 200px !important; height: 50px !important; font-family: 'Poppins', sans-serif !important; font-weight: 600 !important; font-size: 16px !important; }",
      ".btn-brand:hover, .btn-brand:focus { background-color: #3a0970 !important; border-color: #3a0970 !important; }",
      ".register-button .btn-brand, .login-button-width { border-radius: 200px !important; height: 50px !important; }",
      ".login-button-width { background-color: #490B8A !important; border-color: #490B8A !important; border-radius: 200px !important; }",
      ".btn-tpa { display: none !important; }",
      "[class*='btn-oa2-'] { display: none !important; }",
      ".mt-4.mb-3.h4 { display: none !important; }",
      "button.btn-link.btn-sm.text-body.p-0 { display: none !important; }",
      "header, footer, .footer-container { display: none !important; }",
      ".layout { min-height: 100vh !important; }",
      ".layout > .w-50 { min-height: 100vh !important; }",
      "@media (max-width: 991px) {",
      "  .content { max-width: 100% !important; padding: 0 1.5rem !important; }",
      "  .layout > .w-50:first-child .col-md-9 { min-height: auto !important; padding: 40px 30px !important; }",
      "  .layout .w-50 h1, .layout .w-50 .display-1 { font-size: 32px !important; line-height: 44px !important; }",
      "}"
    ].join('\\n');
    document.head.appendChild(style);

    var observer = new MutationObserver(function(mutations, obs) {
      var heading = document.querySelector('.layout h1');
      if (heading && !heading.getAttribute('data-vai')) {
        heading.setAttribute('data-vai', 'true');
        heading.innerHTML = 'Shaping the<br/>Future of <span class="vai-green-underline">Veterinary</span> Medicine';
      }
      var logo = document.querySelector('img.logo');
      if (logo && !logo.getAttribute('data-vai')) {
        logo.setAttribute('data-vai', 'true');
        logo.src = vaiLogoBase64;
        logo.alt = 'VAI';
      }
      if (logo && !document.getElementById('vai-brand-text')) {
        var brandText = document.createElement('div');
        brandText.id = 'vai-brand-text';
        brandText.textContent = 'Veterinary Academy International';
        if (logo.parentElement) {
          logo.parentElement.insertBefore(brandText, logo.nextSibling);
        }
      }
      if (heading && heading.getAttribute('data-vai') && logo && logo.getAttribute('data-vai') && document.getElementById('vai-brand-text')) {
        obs.disconnect();
      }
    });

    function startObserving() {
      if (document.body) {
        observer.observe(document.body, { childList: true, subtree: true });
      }
    }
    if (document.body) {
      startObserving();
    } else {
      document.addEventListener('DOMContentLoaded', startObserving);
    }
    setTimeout(function() { observer.disconnect(); }, 15000);
  })();
}
""",
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

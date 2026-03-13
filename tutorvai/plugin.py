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


# VAI Learner Dashboard MFE styling — custom navbar, empty state, recommended section, footer
hooks.Filters.ENV_PATCHES.add_item(
    (
        "mfe-env-config-buildtime-definitions",
        """
if (process.env.APP_ID === 'learner-dashboard') {
  (function() {
    var lmsBase = '{% if ENABLE_HTTPS %}https://{{ LMS_HOST }}{% else %}http://{{ LMS_HOST }}:8000{% endif %}';
    var vaiDarkLogo = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNzAiIGhlaWdodD0iNDUiIHZpZXdCb3g9IjAgMCA3MCA0NSIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGcgY2xpcC1wYXRoPSJ1cmwoI2NsaXAwXzIwMDFfMTYxOSkiPgo8cGF0aCBkPSJNMCAxMi4wODM4QzQuMDk3NzIgMTIuMzExMiA5LjA0NDY0IDEyLjg5OTMgMTEuODYyMyAxNi4yNDZDMTQuNDA1MiAxOS4yNjY2IDE2LjU0ODUgMjcuMTgzMyAxOS44MDQ5IDI4LjU5MTZDMjEuNTkwNyAyOS4zNjQ3IDIzLjY0MDMgMjguOTA1MiAyNS4yMjYzIDI3Ljg2N0MyNS4zMzU2IDI3Ljc5NjUgMjUuNDc5MiAyNy44MDEyIDI1LjQzNzEgMjcuNjA2N0MyMy41NDUxIDI4LjEzMDUgMjEuMTgzMyAyNy4xNDg4IDIwLjE5NTEgMjUuNDU1QzE5LjAwMjUgMjMuNDExNSAxOS42MTYgMjEuNjcwNyAyMC40OTk1IDE5LjY4NTNDMjIuMTAxMiAxNi4wODE0IDI0LjAxODEgMTIuMjQzOCAyNS43ODk5IDguNzA1NzRDMjguODEyIDIuNjc0MTEgMzIuNzMzNCAwLjMwMTI5OSAzOS40ODAyIDAuMDc3MDM0N0MzOS42ODk0IDAuMDcwNzYxNSAzOS44ODQ1IC0wLjExNTg2NCA0MC4wMzQzIDAuMTE5Mzc4TDIwLjM1MjggNDIuOTUyNEMxOS4wMDg3IDQ1LjMwNjQgMTUuNDMwOCA0NS4wMjcyIDE0LjE1MzkgNDIuNzYxTDAgMTIuMDgzOFoiIGZpbGw9IiM0OTBCOEEiLz4KPHBhdGggZD0iTTYxLjgwNDcgMzEuMTIyNkg1NS45MTQ5TDUzLjcyNDggMjUuOTA0OUw0Mi43MzUxIDI1Ljg4NjFMNDAuNjM0IDMxLjEyMjZIMzQuNzg2M0wzNC42OTQyIDMwLjk0NjlMNDQuOTk1NSA1LjE4Nzg4TDQ1LjI4MTIgNS4wNDUxN0M0Ny4yMTA2IDUuMjMzMzYgNDkuNTYgNC44MTMwNiA1MS40Mzc5IDUuMDQ1MTdDNTEuNTMxNiA1LjA1NjE0IDUxLjYyODMgNS4wNDA0NiA1MS42OTA4IDUuMTM0NTZMNjEuODA0NyAzMS4xMjI2Wk01MS45MDMxIDIwLjgzMTVMNDguNDAxNyAxMS4wNTQ4TDQ0LjU2MTUgMjAuODMxNUg1MS45MDMxWiIgZmlsbD0iIzQ5MEI4QSIvPgo8cGF0aCBkPSJNNjkuOTk5OSAzMS4wMzc5QzY4Ljc5MTcgMzEuMDU5OSA2Ny41NzcyIDMxLjAwOTcgNjYuMzY4OSAzMS4wMzQ4QzY2LjAxOTMgMzEuMDQyNiA2NC4zOTczIDMxLjI4MjYgNjQuMjMxOSAzMS4wMzk1QzY0LjE4MDQgMzAuOTc4MyA2NC4yODE4IDMwLjkzMTMgNjQuMjgxOCAzMC45MDkzVjUuMDUxNDRINjkuODczNUw3MC4wMDE1IDUuMTgwMDRWMzEuMDM3OUg2OS45OTk5WiIgZmlsbD0iIzQ5MEI4QSIvPgo8L2c+CjxkZWZzPgo8Y2xpcFBhdGggaWQ9ImNsaXAwXzIwMDFfMTYxOSI+CjxyZWN0IHdpZHRoPSI3MCIgaGVpZ2h0PSI0NC41OTI2IiBmaWxsPSIjNDkwQjhBIi8+CjwvY2xpcFBhdGg+CjwvZGVmcz4KPC9zdmc+Cg==';
    var vaiWhiteLogo = 'data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNzAiIGhlaWdodD0iNDUiIHZpZXdCb3g9IjAgMCA3MCA0NSIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPGcgY2xpcC1wYXRoPSJ1cmwoI2NsaXAwXzIwMDFfMTYxOSkiPgo8cGF0aCBkPSJNMCAxMi4wODM4QzQuMDk3NzIgMTIuMzExMiA5LjA0NDY0IDEyLjg5OTMgMTEuODYyMyAxNi4yNDZDMTQuNDA1MiAxOS4yNjY2IDE2LjU0ODUgMjcuMTgzMyAxOS44MDQ5IDI4LjU5MTZDMjEuNTkwNyAyOS4zNjQ3IDIzLjY0MDMgMjguOTA1MiAyNS4yMjYzIDI3Ljg2N0MyNS4zMzU2IDI3Ljc5NjUgMjUuNDc5MiAyNy44MDEyIDI1LjQzNzEgMjcuNjA2N0MyMy41NDUxIDI4LjEzMDUgMjEuMTgzMyAyNy4xNDg4IDIwLjE5NTEgMjUuNDU1QzE5LjAwMjUgMjMuNDExNSAxOS42MTYgMjEuNjcwNyAyMC40OTk1IDE5LjY4NTNDMjIuMTAxMiAxNi4wODE0IDI0LjAxODEgMTIuMjQzOCAyNS43ODk5IDguNzA1NzRDMjguODEyIDIuNjc0MTEgMzIuNzMzNCAwLjMwMTI5OSAzOS40ODAyIDAuMDc3MDM0N0MzOS42ODk0IDAuMDcwNzYxNSAzOS44ODQ1IC0wLjExNTg2NCA0MC4wMzQzIDAuMTE5Mzc4TDIwLjM1MjggNDIuOTUyNEMxOS4wMDg3IDQ1LjMwNjQgMTUuNDMwOCA0NS4wMjcyIDE0LjE1MzkgNDIuNzYxTDAgMTIuMDgzOFoiIGZpbGw9IndoaXRlIi8+CjxwYXRoIGQ9Ik02MS44MDQ3IDMxLjEyMjZINTUuOTE0OUw1My43MjQ4IDI1LjkwNDlMNDIuNzM1MSAyNS44ODYxTDQwLjYzNCAzMS4xMjI2SDM0Ljc4NjNMMzQuNjk0MiAzMC45NDY5TDQ0Ljk5NTUgNS4xODc4OEw0NS4yODEyIDUuMDQ1MTdDNDcuMjEwNiA1LjIzMzM2IDQ5LjU2IDQuODEzMDYgNTEuNDM3OSA1LjA0NTE3QzUxLjUzMTYgNS4wNTYxNCA1MS42MjgzIDUuMDQwNDYgNTEuNjkwOCA1LjEzNDU2TDYxLjgwNDcgMzEuMTIyNlpNNTEuOTAzMSAyMC44MzE1TDQ4LjQwMTcgMTEuMDU0OEw0NC41NjE1IDIwLjgzMTVINTEuOTAzMVoiIGZpbGw9IndoaXRlIi8+CjxwYXRoIGQ9Ik02OS45OTk5IDMxLjAzNzlDNjguNzkxNyAzMS4wNTk5IDY3LjU3NzIgMzEuMDA5NyA2Ni4zNjg5IDMxLjAzNDhDNjYuMDE5MyAzMS4wNDI2IDY0LjM5NzMgMzEuMjgyNiA2NC4yMzE5IDMxLjAzOTVDNjQuMTgwNCAzMC45NzgzIDY0LjI4MTggMzAuOTMxMyA2NC4yODE4IDMwLjkwOTNWNS4wNTE0NEg2OS44NzM1TDcwLjAwMTUgNS4xODAwNFYzMS4wMzc5SDY5Ljk5OTlaIiBmaWxsPSJ3aGl0ZSIvPgo8L2c+CjxkZWZzPgo8Y2xpcFBhdGggaWQ9ImNsaXAwXzIwMDFfMTYxOSI+CjxyZWN0IHdpZHRoPSI3MCIgaGVpZ2h0PSI0NC41OTI2IiBmaWxsPSJ3aGl0ZSIvPgo8L2NsaXBQYXRoPgo8L2RlZnM+Cjwvc3ZnPgo=';
    var catSvg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200"><defs><linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#F3EDFF"/><stop offset="100%" style="stop-color:#E8DEFF"/></linearGradient></defs><circle cx="100" cy="100" r="90" fill="url(#bg)"/><g transform="translate(50, 30)"><path d="M15 40 L25 10 L35 35" fill="#490B8A" stroke="#490B8A" stroke-width="2"/><path d="M65 40 L75 10 L85 35" fill="#490B8A" stroke="#490B8A" stroke-width="2"/><ellipse cx="50" cy="80" rx="45" ry="50" fill="#490B8A"/><ellipse cx="50" cy="85" rx="38" ry="35" fill="#5C1FA0"/><circle cx="35" cy="65" r="12" fill="white"/><circle cx="65" cy="65" r="12" fill="white"/><circle cx="37" cy="63" r="6" fill="#101114"/><circle cx="67" cy="63" r="6" fill="#101114"/><circle cx="39" cy="61" r="2" fill="white"/><circle cx="69" cy="61" r="2" fill="white"/><ellipse cx="50" cy="82" rx="5" ry="3" fill="#FF8FAB"/><path d="M40 90 Q50 100 60 90" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"/><line x1="15" y1="75" x2="30" y2="78" stroke="white" stroke-width="1.5" stroke-linecap="round"/><line x1="15" y1="82" x2="30" y2="82" stroke="white" stroke-width="1.5" stroke-linecap="round"/><line x1="70" y1="78" x2="85" y2="75" stroke="white" stroke-width="1.5" stroke-linecap="round"/><line x1="70" y1="82" x2="85" y2="82" stroke="white" stroke-width="1.5" stroke-linecap="round"/><circle cx="28" cy="45" r="8" fill="none" stroke="#2DBE6C" stroke-width="3"/><line x1="34" y1="51" x2="42" y2="59" stroke="#2DBE6C" stroke-width="3" stroke-linecap="round"/></g></svg>';

    var fontLink = document.createElement('link');
    fontLink.href = 'https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&display=swap';
    fontLink.rel = 'stylesheet';
    document.head.appendChild(fontLink);

    var style = document.createElement('style');
    style.id = 'vai-dashboard-styles';
    style.textContent = [
      "@font-face { font-family: 'Garet'; src: url('" + lmsBase + "/static/vai/fonts/Garet-Book.otf') format('opentype'); font-weight: 400; font-style: normal; font-display: swap; }",
      "@font-face { font-family: 'Garet'; src: url('" + lmsBase + "/static/vai/fonts/Garet-Regular.otf') format('opentype'); font-weight: 500; font-style: normal; font-display: swap; }",
      "@font-face { font-family: 'Garet'; src: url('" + lmsBase + "/static/vai/fonts/Garet-Bold.otf') format('opentype'); font-weight: 700; font-style: normal; font-display: swap; }",
      "@font-face { font-family: 'Garet'; src: url('" + lmsBase + "/static/vai/fonts/Garet-ExtraBold.otf') format('opentype'); font-weight: 800; font-style: normal; font-display: swap; }",
      "html body { font-family: 'Garet', 'Poppins', 'Open Sans', 'Helvetica Neue', Helvetica, Arial, sans-serif !important; background: #FAFAFA !important; }",
      "html header.site-header-desktop { background: #FFFFFF !important; border: none !important; padding: 0 !important; box-shadow: 0px 1px 2px 0px rgba(0,0,0,0.06), 0px 1px 3px 0px rgba(0,0,0,0.10) !important; }",
      "html header .container-fluid { max-width: 1600px !important; margin: 0 auto !important; padding: 0 15px !important; }",
      "html header .nav-container { min-height: auto !important; }",
      "html header .logo { display: flex !important; align-items: center !important; }",
      "html header .logo img { height: 24px !important; width: auto !important; }",
      "html header .main-nav { margin-left: 38px !important; }",
      "html header .main-nav .nav-link { font-size: 14px !important; font-weight: 500 !important; line-height: 22px !important; color: #374151 !important; background: transparent !important; padding: 20px 0 !important; margin: 0 16px 0 0 !important; border-radius: 0 !important; border-bottom: 2px solid transparent !important; transition: color 0.2s, border-color 0.2s !important; }",
      "html header .main-nav .nav-link:hover, html header .main-nav .nav-link.active { color: #111827 !important; border-bottom: 2px solid #490B8A !important; background: transparent !important; }",
      "html header.site-header-desktop .menu-trigger { padding: 9px 15px !important; background: #F5ECFF !important; color: #490B8A !important; font-size: 14px !important; font-weight: 500 !important; line-height: 20px !important; border-radius: 200px !important; border: none !important; margin: 12px 0 !important; }",
      "html header.site-header-desktop .menu-trigger .avatar { display: none !important; }",
      "html header.site-header-desktop .menu-trigger svg:last-child { display: none !important; }",
      "html header.site-header-desktop .menu-trigger::after { content: '' !important; margin: 4px 0 0 4px !important; border: 2px solid #490B8A !important; border-width: 2px 2px 0 0 !important; transform: rotate(135deg) !important; height: 5px !important; width: 5px !important; display: inline-block !important; vertical-align: top !important; position: relative !important; top: 2px !important; }",
      "html header.site-header-mobile { background: #FFFFFF !important; border: none !important; box-shadow: 0px 1px 2px 0px rgba(0,0,0,0.06), 0px 1px 3px 0px rgba(0,0,0,0.10) !important; }",
      "html header.site-header-mobile .logo img { height: 24px !important; width: auto !important; }",
      "html header.site-header-mobile button { background: transparent !important; border: none !important; color: #101114 !important; padding: 8px !important; }",
      "html header.site-header-mobile button svg { color: #101114 !important; }",
      "html main { background: #FAFAFA !important; }",
      "html main > div#dashboard-container { max-width: 1200px !important; margin: 0 auto !important; padding: 0 40px !important; }",
      "html h1[class] { display: none !important; }",
      "html .sidebar-column { display: none !important; }",
      "html .course-list-column { flex: 0 0 100% !important; max-width: 100% !important; padding: 0 !important; }",
      "html .container-mw-xl { max-width: 100% !important; padding: 0 !important; }",
      "html #dashboard-content .row { margin: 0 !important; }",
      "html .course-list-container { padding-top: 20px !important; }",
      "html .course-list-container > .d-flex.flex-column { display: grid !important; grid-template-columns: repeat(2, 1fr) !important; gap: 24px !important; }",
      "@media (max-width: 900px) { html .course-list-container > .d-flex.flex-column { grid-template-columns: 1fr !important; } html body .course-card .pgn__card-wrapper-image-cap.horizontal, html body .course-card .pgn__card-wrapper-image-cap { width: 100% !important; min-width: 100% !important; max-width: 100% !important; height: 180px !important; margin: 0 !important; border-radius: 14px 14px 0 0 !important; } html body .course-card .pgn__card.horizontal, html body .course-card .pgn__card { min-height: auto !important; } html body .course-card .pgn__card-body { min-height: auto !important; padding: 16px !important; } }",
      "html .course-card { margin-bottom: 0 !important; border-radius: 14px !important; overflow: hidden !important; border: 1px solid #E8E8E8 !important; box-shadow: 0 1px 4px rgba(0,0,0,0.06) !important; background: #FFFFFF !important; }",
      "html .course-card .pgn__card.horizontal { background: #FFFFFF !important; border: none !important; border-radius: 14px 14px 0 0 !important; box-shadow: none !important; min-height: 256px !important; }",
      "html .course-card .pgn__card .d-flex.flex-column.w-100 { border-radius: 0 !important; }",
      "html .course-card .pgn__card-wrapper-image-cap.horizontal { width: 208px !important; min-width: 208px !important; max-width: 208px !important; height: 240px !important; margin: 8px !important; border-radius: 12px !important; overflow: hidden !important; flex-shrink: 0 !important; }",
      "html .course-card .pgn__card-image-cap { width: 100% !important; height: 100% !important; object-fit: cover !important; }",
      "html .course-card .pgn__card-body { display: flex !important; flex-direction: column !important; justify-content: space-between !important; padding: 18px 16px 18px 18px !important; min-height: 220px !important; }",
      "html .course-card .course-card-title { font-family: 'Garet', 'Poppins', sans-serif !important; font-weight: 800 !important; font-size: 20px !important; line-height: 30px !important; color: #101114 !important; text-decoration: none !important; }",
      "html .course-card .course-card-title:hover { text-decoration: none !important; color: #490B8A !important; }",
      "html .course-card .pgn__card-header { padding: 0 !important; margin-bottom: 0 !important; }",
      "html .course-card .pgn__card-header-title-md h3 { margin: 0 !important; }",
      "html .course-card .pgn__card-section { display: none !important; }",
      "html .vai-card-meta { display: flex; flex-direction: column; gap: 10px; margin-top: 16px; }",
      "html .vai-card-meta-row { display: flex; align-items: center; gap: 10px; font-family: 'Garet', 'Poppins', sans-serif; font-size: 16px; color: #252525; line-height: normal; }",
      "html .vai-card-meta-row svg { width: 24px; height: 24px; flex-shrink: 0; }",
      "html .course-card .pgn__card-header-actions .btn-icon { color: #101114 !important; }",
      "html .course-card .pgn__card-footer { padding: 0 !important; border-top: none !important; margin-top: auto !important; }",
      "html .course-card .pgn__card-footer.horizontal { flex-direction: row !important; }",
      "html .course-card .pgn__action-row { gap: 10px !important; flex-wrap: nowrap !important; }",
      "html .course-card .btn.btn-primary { background: #490B8A !important; border-color: #490B8A !important; border-radius: 200px !important; height: 45px !important; padding: 10px 22px !important; font-family: 'Garet', 'Poppins', sans-serif !important; font-weight: 700 !important; font-size: 16px !important; line-height: 1 !important; color: white !important; display: inline-flex !important; align-items: center !important; gap: 10px !important; white-space: nowrap !important; }",
      "html .course-card .btn.btn-primary:hover { background: #3a0970 !important; border-color: #3a0970 !important; }",
      "html .course-card .btn.btn-outline-primary, html .course-card .btn.btn-tertiary { background: transparent !important; border: 1px solid #490B8A !important; color: #490B8A !important; border-radius: 200px !important; height: 45px !important; padding: 10px 22px !important; font-family: 'Garet', 'Poppins', sans-serif !important; font-weight: 700 !important; font-size: 16px !important; line-height: 1 !important; display: inline-flex !important; align-items: center !important; gap: 10px !important; white-space: nowrap !important; }",
      "html .course-card-banners { background: #eee !important; border-radius: 0 0 14px 14px !important; }",
      "html .course-card-banners .alert { background: #eee !important; border: none !important; border-radius: 0 0 14px 14px !important; margin: 0 !important; padding: 8px 16px !important; font-family: 'Garet', 'Poppins', sans-serif !important; font-size: 12px !important; color: #101114 !important; min-height: 40px !important; max-height: 40px !important; height: 40px !important; display: flex !important; align-items: center !important; }",
      "html .course-card-banners .alert .pgn__icon { width: 24px !important; height: 24px !important; }",
      "html .course-card-banners .alert-message-content { font-size: 12px !important; line-height: normal !important; }",
      "html .course-card-banners .vai-purple { color: #490B8A !important; font-weight: 500 !important; }",
      "html .course-list-heading-container { display: block !important; margin-bottom: 24px !important; }",
      "html .course-list-heading-container h2 { font-family: 'Garet', 'Poppins', sans-serif !important; font-weight: 800 !important; font-size: 32px !important; color: #101114 !important; margin: 0 0 8px !important; }",
      "html #no-courses-content-view { flex-direction: column !important; align-items: center !important; text-align: center !important; padding: 60px 20px 40px !important; background: #FFFFFF !important; border-radius: 16px !important; border: 1px solid #E8E8E8 !important; margin-bottom: 0 !important; }",
      "html #no-courses-content-view > img { display: none !important; }",
      "html #no-courses-content-view > h1 { font-family: 'Garet', 'Poppins', sans-serif !important; font-weight: 800 !important; font-size: 32px !important; line-height: 1.3 !important; color: #101114 !important; margin-bottom: 12px !important; }",
      "html #no-courses-content-view > p { font-size: 16px !important; color: #666666 !important; margin-bottom: 32px !important; }",
      "html #no-courses-content-view .btn-brand, html a.btn-brand { background: transparent !important; border: 2px solid #490B8A !important; color: #490B8A !important; border-radius: 200px !important; font-weight: 600 !important; font-size: 15px !important; padding: 12px 32px !important; transition: all 0.2s ease !important; text-decoration: none !important; }",
      "html #no-courses-content-view .btn-brand:hover, html a.btn-brand:hover { background: #490B8A !important; color: #FFFFFF !important; }",
      "html #no-courses-content-view .btn-brand .pgn__icon, html a.btn-brand .pgn__icon { display: none !important; }",
      "html #vai-cat-illustration { width: 200px; height: 200px; margin-bottom: 24px; }",
      "html #vai-recommended-section { max-width: 1600px; margin: 0 auto; padding: 50px 15px 60px; }",
      "html .rfy-header { display: flex; align-items: flex-end; justify-content: space-between; margin: 0 0 28px; gap: 20px; flex-wrap: wrap; }",
      "html .rfy-text { max-width: 761px; }",
      "html .rfy-text h2 { font-family: 'Garet', 'Poppins', sans-serif !important; font-size: 28px; font-weight: 800; line-height: 1.3; color: #101114; margin: 0 0 10px; }",
      "@media (min-width: 768px) { html .rfy-text h2 { font-size: 42px; line-height: 70px; margin: 0; } }",
      "html .rfy-text p { font-family: 'Garet', 'Poppins', sans-serif !important; font-size: 16px; line-height: 1.5; color: #101114; margin: 0; }",
      "@media (min-width: 768px) { html .rfy-text p { font-size: 20px; } }",
      "html .rfy-arrows { display: flex; gap: 8px; flex-shrink: 0; }",
      "html .rfy-arrow { display: flex; align-items: center; justify-content: center; width: 50px; height: 50px; border: 1px solid #490B8A; border-radius: 200px; background: transparent; cursor: pointer; transition: all 0.2s ease; color: #490B8A; padding: 0; }",
      "@media (min-width: 768px) { html .rfy-arrow { width: 108px; } }",
      "html .rfy-arrow svg { width: 24px; height: 24px; flex-shrink: 0; }",
      "html .rfy-arrow:hover { background: #490B8A; color: #fff; }",
      "html .rfy-arrow:hover svg { stroke: #fff; }",
      "html .rfy-carousel-wrapper { overflow: hidden; }",
      "html .rfy-carousel { display: flex; gap: 14px; overflow-x: auto; scroll-behavior: smooth; scrollbar-width: none; padding: 10px 0 20px; }",
      "html .rfy-carousel::-webkit-scrollbar { display: none; }",
      "html .rfy-card { flex: 0 0 240px; height: 340px; border-radius: 12px; overflow: hidden; position: relative; cursor: pointer; transition: all 0.35s ease; text-decoration: none !important; display: block; background: #fff; border: 6px solid transparent; }",
      "@media (min-width: 576px) { html .rfy-card { flex: 0 0 260px; height: 370px; } }",
      "@media (min-width: 768px) { html .rfy-card { flex: 0 0 282px; height: 399px; } }",
      "html .rfy-card-image { position: absolute; inset: 0; z-index: 0; }",
      "html .rfy-card-image img { width: 100%; height: 100%; object-fit: cover; display: block; }",
      "html .rfy-card-gradient { position: absolute; left: 0; right: 0; bottom: 0; height: 50%; background: linear-gradient(to bottom, rgba(16,17,20,0), #101114); transition: height 0.35s ease; pointer-events: none; z-index: 1; }",
      "html .rfy-card-content { position: absolute; left: 18px; right: 18px; bottom: 18px; display: flex; flex-direction: column; gap: 11px; transition: bottom 0.35s ease; z-index: 2; }",
      "html .rfy-card-tag { display: inline-block !important; background: #8fe389; color: #101114 !important; font-family: 'Garet', 'Poppins', sans-serif !important; font-size: 14px; line-height: 24px; padding: 2px 5px; width: fit-content; white-space: nowrap; }",
      "html .rfy-card-title { color: #fff !important; font-family: 'Garet', 'Poppins', sans-serif !important; font-size: 15px; font-weight: 800; line-height: 1.3; margin: 0 !important; padding: 0 !important; max-width: 200px; display: -webkit-box !important; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; border: none !important; }",
      "html .rfy-card-buttons { position: absolute; left: 18px; right: 18px; bottom: 25px; display: flex; flex-direction: column; gap: 10px; opacity: 0; transform: translateY(10px); transition: all 0.3s ease 0.05s; pointer-events: none; z-index: 3; }",
      "html .rfy-btn-primary { display: flex !important; align-items: center; justify-content: center; gap: 10px; height: 50px; max-height: 50px; box-sizing: border-box; background: #fff !important; color: #490B8A !important; font-family: 'Garet', 'Poppins', sans-serif !important; font-size: 16px; font-weight: 700; line-height: 1 !important; border-radius: 200px; padding: 10px 22px; white-space: nowrap; text-decoration: none !important; }",
      "html .rfy-btn-primary svg { width: 20px; height: 20px; flex-shrink: 0; stroke: #490B8A; }",
      "html .rfy-btn-outline { display: flex !important; align-items: center; justify-content: center; height: 50px; max-height: 50px; box-sizing: border-box; border: 1px solid #fff; background: transparent !important; color: #fff !important; font-family: 'Garet', 'Poppins', sans-serif !important; font-size: 16px; font-weight: 700; line-height: 1 !important; border-radius: 200px; padding: 10px 22px; white-space: nowrap; text-decoration: none !important; }",
      "html .rfy-card:hover { border-color: #490B8A; box-shadow: 10px 10px 20px rgba(0,0,0,0.25); }",
      "html .rfy-card:hover .rfy-card-gradient { height: 100%; }",
      "html .rfy-card:hover .rfy-card-content { bottom: 155px; }",
      "html .rfy-card:hover .rfy-card-buttons { opacity: 1; transform: translateY(0); pointer-events: auto; }",
      "html .rfy-cta-wrapper { text-align: center; padding: 30px 0 0; }",
      "html .rfy-browse-btn { display: inline-flex; align-items: center; gap: 10px; padding: 10px 22px; height: 50px; border: 1px solid #490B8A; border-radius: 200px; background: #fff; color: #490B8A !important; font-family: 'Garet', 'Poppins', sans-serif !important; font-size: 16px; font-weight: 700; text-decoration: none !important; transition: all 0.2s ease; }",
      "html .rfy-browse-btn svg { width: 20px; height: 20px; flex-shrink: 0; }",
      "html .rfy-browse-btn:hover { background: #490B8A; color: #fff !important; text-decoration: none; }",
      "html .rfy-browse-btn:hover svg { stroke: #fff; }",
      "html footer.footer { display: none !important; }",
      "html .wrapper-footer { background: #101114 !important; border-top: none !important; padding: 89px 0 41px !important; box-shadow: none !important; }",
      "@media (max-width: 767px) { html .wrapper-footer { padding: 40px 0 30px !important; } }",
      "html #vai-footer { margin: 0 auto; padding: 0 120px; max-width: 1200px; box-sizing: border-box; }",
      "@media (max-width: 767px) { html #vai-footer { padding: 0 20px; } }",
      "html .footer-main { display: flex; justify-content: space-between; }",
      "@media (max-width: 767px) { html .footer-main { flex-direction: column; gap: 40px; } }",
      "html .footer-brand { width: 180px; flex-shrink: 0; }",
      "@media (max-width: 767px) { html .footer-brand { width: 100%; } }",
      "html .footer-logo { width: 70px; height: auto; display: block; }",
      "html .footer-social { margin-top: 73px; }",
      "@media (max-width: 767px) { html .footer-social { margin-top: 30px; } }",
      "html .footer-social p { font-size: 14px; color: #fff; margin: 0 0 15px; font-weight: 400; }",
      "html .footer-social-icons { display: flex; gap: 18px; align-items: center; }",
      "html .footer-social-icons a { display: flex; align-items: center; transition: opacity 0.2s; text-decoration: none; }",
      "html .footer-social-icons a:hover { opacity: 0.7; }",
      "html .footer-social-icons a svg { width: 24px; height: 24px; }",
      "html .footer-links { display: flex; gap: 30px; }",
      "@media (max-width: 767px) { html .footer-links { flex-wrap: wrap; gap: 30px; } }",
      "html .footer-links-col { width: 170px; }",
      "@media (max-width: 767px) { html .footer-links-col { width: calc(50% - 15px); } }",
      "html .footer-links-col h4 { font-family: 'Garet', 'Poppins', sans-serif !important; font-size: 20px; font-weight: 500; color: #fff; margin: 0 0 20px; }",
      "html .footer-links-col a { display: block; font-size: 14px; font-weight: 400; color: #fff; text-decoration: none; line-height: normal; margin-bottom: 10px; transition: opacity 0.2s; }",
      "html .footer-links-col a:hover { opacity: 0.7; text-decoration: none; color: #fff; }",
      "html .footer-contact-item { display: flex; gap: 10px; align-items: center; margin-bottom: 10px; }",
      "html .footer-contact-item svg { width: 20px; height: 20px; flex-shrink: 0; }",
      "html .footer-contact-item a { margin-bottom: 0; }",
      "html .footer-bottom { margin-top: 30px; }",
      "html .footer-separator { height: 1px; background: rgba(255,255,255,0.2); }",
      "html .footer-copyright { text-align: center; font-size: 14px; color: #fff; margin-top: 21px; font-weight: 400; }"
    ].join('\\n');
    document.head.appendChild(style);

    var footerHtml =
      '<div class="wrapper-footer">' +
        '<footer id="vai-footer" class="tutor-container">' +
          '<div class="footer-main">' +
            '<div class="footer-brand">' +
              '<img class="footer-logo" src="' + vaiWhiteLogo + '" alt="VAI Logo">' +
              '<div class="footer-social"><p>Connect With Us:</p>' +
                '<div class="footer-social-icons">' +
                  '<a href="#" aria-label="LinkedIn" rel="noopener" target="_blank"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z" fill="white"/></svg></a>' +
                  '<a href="#" aria-label="Facebook" rel="noopener" target="_blank"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M24 12c0-6.627-5.373-12-12-12S0 5.373 0 12c0 5.99 4.388 10.954 10.125 11.854V15.47H7.078V12h3.047V9.356c0-3.007 1.792-4.668 4.533-4.668 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874V12h3.328l-.532 3.47h-2.796v8.385C19.612 22.954 24 17.99 24 12z" fill="white"/></svg></a>' +
                  '<a href="#" aria-label="Instagram" rel="noopener" target="_blank"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 0C8.74 0 8.333.015 7.053.072 5.775.132 4.905.333 4.14.63c-.789.306-1.459.717-2.126 1.384S.935 3.35.63 4.14C.333 4.905.131 5.775.072 7.053.012 8.333 0 8.74 0 12s.015 3.667.072 4.947c.06 1.277.261 2.148.558 2.913.306.788.717 1.459 1.384 2.126.667.666 1.336 1.079 2.126 1.384.766.296 1.636.499 2.913.558C8.333 23.988 8.74 24 12 24s3.667-.015 4.947-.072c1.277-.06 2.148-.262 2.913-.558.788-.306 1.459-.718 2.126-1.384.666-.667 1.079-1.335 1.384-2.126.296-.765.499-1.636.558-2.913.06-1.28.072-1.687.072-4.947s-.015-3.667-.072-4.947c-.06-1.277-.262-2.149-.558-2.913-.306-.789-.718-1.459-1.384-2.126C21.319 1.347 20.651.935 19.86.63c-.765-.297-1.636-.499-2.913-.558C15.667.012 15.26 0 12 0zm0 2.16c3.203 0 3.585.016 4.85.071 1.17.055 1.805.249 2.227.415.562.217.96.477 1.382.896.419.42.679.819.896 1.381.164.422.36 1.057.413 2.227.057 1.266.07 1.646.07 4.85s-.015 3.585-.074 4.85c-.061 1.17-.256 1.805-.421 2.227-.224.562-.479.96-.899 1.382-.419.419-.824.679-1.38.896-.42.164-1.065.36-2.235.413-1.274.057-1.649.07-4.859.07-3.211 0-3.586-.015-4.859-.074-1.171-.061-1.816-.256-2.236-.421-.569-.224-.96-.479-1.379-.899-.421-.419-.69-.824-.9-1.38-.165-.42-.359-1.065-.42-2.235-.045-1.26-.061-1.649-.061-4.844 0-3.196.016-3.586.061-4.861.061-1.17.255-1.814.42-2.234.21-.57.479-.96.9-1.381.419-.419.81-.689 1.379-.898.42-.166 1.051-.361 2.221-.421 1.275-.045 1.65-.06 4.859-.06l.045.03zm0 3.678a6.162 6.162 0 100 12.324 6.162 6.162 0 100-12.324zM12 16c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4zm7.846-10.405a1.441 1.441 0 11-2.882 0 1.441 1.441 0 012.882 0z" fill="white"/></svg></a>' +
                  '<a href="#" aria-label="X" rel="noopener" target="_blank"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" fill="white"/></svg></a>' +
                '</div>' +
              '</div>' +
            '</div>' +
            '<div class="footer-links">' +
              '<div class="footer-links-col"><h4>Programs</h4><a href="#">Small Animal Surgery</a><a href="#">Diagnostic Imaging</a><a href="#">Emergency &amp; Critical Care</a><a href="#">Practice Management</a></div>' +
              '<div class="footer-links-col"><h4>Quick Links</h4><a href="#">About Us</a><a href="#">Courses</a><a href="#">Clinic Subscriptions</a><a href="#">Insights</a><a href="#">Contact Us</a></div>' +
              '<div class="footer-links-col"><h4>Contact</h4>' +
                '<div class="footer-contact-item"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M22 16.92v3a2 2 0 01-2.18 2 19.79 19.79 0 01-8.63-3.07 19.5 19.5 0 01-6-6 19.79 19.79 0 01-3.07-8.67A2 2 0 014.11 2h3a2 2 0 012 1.72c.127.96.361 1.903.7 2.81a2 2 0 01-.45 2.11L8.09 9.91a16 16 0 006 6l1.27-1.27a2 2 0 012.11-.45c.907.339 1.85.573 2.81.7A2 2 0 0122 16.92z" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/></svg><a href="mailto:enquire@vai.com">enquire@vai.com</a></div>' +
                '<div class="footer-contact-item"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/><path d="M22 6l-10 7L2 6" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg><a href="tel:+442079460011">+44 20 7946 0011</a></div>' +
              '</div>' +
            '</div>' +
          '</div>' +
          '<div class="footer-bottom"><div class="footer-separator"></div><p class="footer-copyright">&copy; ' + new Date().getFullYear() + ' Veterinary Academy International. All Rights Reserved.</p></div>' +
        '</footer>' +
      '</div>';

    function applyVaiDashboard() {
      var logoImg = document.querySelector('header .logo img');
      if (logoImg && !logoImg.getAttribute('data-vai')) {
        logoImg.setAttribute('data-vai', 'true');
        logoImg.src = vaiDarkLogo;
        logoImg.alt = 'VAI';
      }
      var navLinks = document.querySelectorAll('nav[aria-label="Main"] a');
      navLinks.forEach(function(link) {
        if (link.textContent.trim() === 'Discover New') link.textContent = 'Discover';
      });
      var CLOCK_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#252525" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>';
      var FLAG_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#252525" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><line x1="4" y1="22" x2="4" y2="15"/></svg>';
      var FORWARD_SVG = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>';
      document.querySelectorAll('.course-card').forEach(function(card) {
        if (card.getAttribute('data-vai-enhanced')) return;
        card.setAttribute('data-vai-enhanced', 'true');
        var beginBtn = card.querySelector('.btn.btn-primary');
        if (beginBtn && !beginBtn.querySelector('.vai-arrow')) {
          var arrowSpan = document.createElement('span');
          arrowSpan.className = 'vai-arrow';
          arrowSpan.innerHTML = FORWARD_SVG;
          arrowSpan.style.display = 'inline-flex';
          arrowSpan.style.alignItems = 'center';
          beginBtn.appendChild(arrowSpan);
        }
        var cardBody = card.querySelector('.pgn__card-body');
        if (cardBody && !cardBody.querySelector('.vai-card-meta')) {
          var metaDiv = document.createElement('div');
          metaDiv.className = 'vai-card-meta';
          metaDiv.innerHTML = '<div class="vai-card-meta-row">' + CLOCK_SVG + '<span>Self-paced</span></div><div class="vai-card-meta-row">' + FLAG_SVG + '<span>Enrolled</span></div>';
          var cardHeader = cardBody.querySelector('.pgn__card-header');
          if (cardHeader) cardHeader.after(metaDiv);
        }
        var alertMsg = card.querySelector('.course-card-banners .alert-message-content');
        if (alertMsg && !alertMsg.getAttribute('data-vai-styled')) {
          alertMsg.setAttribute('data-vai-styled', 'true');
          var text = alertMsg.textContent || '';
          var gradeMatch = text.match(/(\\d+[\\u200F\\u200E]?%)/);
          if (gradeMatch) {
            alertMsg.innerHTML = 'A <span class="vai-purple">passing grade of ' + gradeMatch[0] + '</span> is required to complete this course successfully.';
          }
        }
      });
      var emptyState = document.getElementById('no-courses-content-view');
      if (emptyState && !emptyState.getAttribute('data-vai')) {
        emptyState.setAttribute('data-vai', 'true');
        var catDiv = document.createElement('div');
        catDiv.id = 'vai-cat-illustration';
        catDiv.innerHTML = catSvg;
        var firstH1 = emptyState.querySelector('h1');
        if (firstH1) { emptyState.insertBefore(catDiv, firstH1); firstH1.textContent = 'Ready to begin your journey?'; }
        var subtitle = emptyState.querySelector('p');
        if (subtitle) subtitle.textContent = 'Explore our courses and start learning today';
        var btn = emptyState.querySelector('.btn-brand');
        if (btn) btn.innerHTML = 'Browse all Courses <span style="margin-left:8px">\\u2192</span>';
      }
      if (!document.getElementById('vai-recommended-section')) {
        var mainEl = document.querySelector('main');
        if (mainEl) {
          var ARROW_LEFT = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><path d="m12 19-7-7 7-7"/></svg>';
          var ARROW_RIGHT = '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>';
          var recSection = document.createElement('div');
          recSection.id = 'vai-recommended-section';
          recSection.innerHTML =
            '<div class="rfy-header">' +
              '<div class="rfy-text"><h2>Recommended for You</h2>' +
              '<p>Explore curated courses designed to enhance your knowledge and practical skills for real-world success.</p></div>' +
              '<div class="rfy-arrows">' +
                '<button class="rfy-arrow rfy-arrow-prev" aria-label="Previous">' + ARROW_LEFT + '</button>' +
                '<button class="rfy-arrow rfy-arrow-next" aria-label="Next">' + ARROW_RIGHT + '</button>' +
              '</div>' +
            '</div>' +
            '<div class="rfy-carousel-wrapper"><div class="rfy-carousel" id="vai-rfy-carousel">' +
              '<div style="height:399px;display:flex;align-items:center;justify-content:center;color:#999;font-size:14px;">Loading courses...</div>' +
            '</div></div>' +
            '<div class="rfy-cta-wrapper"><a href="' + lmsBase + '/courses" class="rfy-browse-btn">Browse all Courses ' + ARROW_RIGHT + '</a></div>';
          mainEl.parentElement.insertBefore(recSection, mainEl.nextSibling);
          fetchCourses();
          setTimeout(function() {
            var carousel = document.getElementById('vai-rfy-carousel');
            var prevBtn = recSection.querySelector('.rfy-arrow-prev');
            var nextBtn = recSection.querySelector('.rfy-arrow-next');
            if (carousel && prevBtn && nextBtn) {
              var scrollAmount = 296;
              prevBtn.addEventListener('click', function() { carousel.scrollBy({ left: -scrollAmount, behavior: 'smooth' }); });
              nextBtn.addEventListener('click', function() { carousel.scrollBy({ left: scrollAmount, behavior: 'smooth' }); });
            }
          }, 100);
        }
      }
      var defaultFooter = document.querySelector('footer.footer');
      if (defaultFooter) defaultFooter.style.display = 'none';
      if (!document.getElementById('vai-footer')) {
        var footerContainer = document.createElement('div');
        footerContainer.innerHTML = footerHtml;
        document.body.appendChild(footerContainer.firstChild);
      }
    }

    function fetchCourses() {
      var carousel = document.getElementById('vai-rfy-carousel');
      if (!carousel) return;
      var GET_STARTED_ARROW = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>';
      fetch(lmsBase + '/api/courses/v1/courses/?page_size=8&ordering=-start')
        .then(function(res) { return res.json(); })
        .then(function(data) {
          var courses = data.results || [];
          if (courses.length === 0) { carousel.innerHTML = '<div style="text-align:center;padding:40px;color:#999;">No courses available yet.</div>'; return; }
          var html = '';
          courses.forEach(function(course) {
            var imgSrc = (course.media && course.media.image && course.media.image.large) ? course.media.image.large : '';
            var aboutUrl = lmsBase + '/courses/' + course.course_id + '/about';
            html += '<a href="' + aboutUrl + '" class="rfy-card">' +
              '<div class="rfy-card-image">' +
                (imgSrc ? '<img src="' + imgSrc + '" alt="' + (course.name || '') + '">' : '<div style="width:100%;height:100%;background:linear-gradient(135deg,#490B8A 0%,#7B2FBE 100%)"></div>') +
              '</div>' +
              '<div class="rfy-card-gradient"></div>' +
              '<div class="rfy-card-content">' +
                '<span class="rfy-card-tag">' + (course.org || 'VAI') + '</span>' +
                '<h3 class="rfy-card-title">' + (course.name || 'Untitled') + '</h3>' +
              '</div>' +
              '<div class="rfy-card-buttons">' +
                '<span class="rfy-btn-primary">Get Started ' + GET_STARTED_ARROW + '</span>' +
                '<span class="rfy-btn-outline">More Info</span>' +
              '</div>' +
            '</a>';
          });
          carousel.innerHTML = html;
        })
        .catch(function() { carousel.innerHTML = '<div style="text-align:center;padding:40px;color:#999;">Could not load courses.</div>'; });
    }

    var observer = new MutationObserver(function() { applyVaiDashboard(); });
    function startObserving() {
      if (document.body) { observer.observe(document.body, { childList: true, subtree: true }); applyVaiDashboard(); }
    }
    if (document.body) startObserving();
    else document.addEventListener('DOMContentLoaded', startObserving);
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

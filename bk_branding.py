"""Single source of truth for product identity — every window title, the
Task Manager process description, the installer, and the release-system
product slug all read from here, so "a different name in every part of the
program" (a direct complaint) cannot happen again: there is exactly one
place this is defined.
"""
import os

PRODUCT_NAME = "Chenkron"
PRODUCT_SLUG = "chenkron"  # release-system product id — lowercase, no spaces
COMPANY_NAME = "Chenkron"
COPYRIGHT = "© Chenkron"

# Sampled directly from the supplied brand mark (App Logo.png /
# Inner Logo.PNG), not invented — this IS the institution's real color.
BRAND_BLUE = "#0F4AAB"
BRAND_BLUE_DARK = "#0B3680"
BRAND_RED = "#E63946"

_HERE = os.path.dirname(os.path.abspath(__file__))


def asset_path(filename: str) -> str:
    """Resolves an asset next to this file, in a PyInstaller-frozen build's
    _internal dir, or next to the exe — same search order the rest of the
    app already uses for 11.png etc., kept consistent here."""
    import sys

    candidates = []
    if hasattr(sys, "_MEIPASS"):
        candidates.append(os.path.join(sys._MEIPASS, filename))
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
        candidates.append(os.path.join(exe_dir, filename))
        candidates.append(os.path.join(exe_dir, "_internal", filename))
    candidates.append(os.path.join(_HERE, filename))
    for c in candidates:
        if os.path.exists(c):
            return c
    return os.path.join(_HERE, filename)


ICON_ICO = asset_path("bk_icon.ico")
ICON_PNG = asset_path("bk_icon.png")
INNER_LOGO_PNG = asset_path("bk_inner_logo.png")

# The shield alone, on transparency — used as the sign-in mark and, very
# faint, as a watermark. Prefers the clean filename so a PyInstaller spec
# does not have to carry "ChatGPT Image ....png".
SHIELD_PNG = (asset_path("bk_shield_clean.png")
              if os.path.exists(asset_path("bk_shield_clean.png"))
              else INNER_LOGO_PNG)
LOCKUP_PNG = (asset_path("bk_lockup.png")
              if os.path.exists(asset_path("bk_lockup.png"))
              else SHIELD_PNG)
DASHBOARD_BRAND_PNG = asset_path("bk_dashboard_brand.png")

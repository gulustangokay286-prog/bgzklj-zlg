"""Single source of truth for product identity — every window title, the
Task Manager process description, the installer, and the release-system
product slug all read from here, so "a different name in every part of the
program" (a direct complaint) cannot happen again: there is exactly one
place this is defined.
"""
import os

PRODUCT_NAME = "BK Planner"
PRODUCT_SLUG = "bkplanner"  # release-system product id — lowercase, no spaces
COMPANY_NAME = "Boğaziçi Koleji"
COPYRIGHT = "© Boğaziçi Koleji"

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
DASHBOARD_BRAND_PNG = asset_path("bk_dashboard_brand.png")

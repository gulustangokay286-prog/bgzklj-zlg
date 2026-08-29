"""
version.py — single source of truth for this build's identity.

APP_BUILD is what the updater compares; it must increase with every release you
publish, and the value passed to publish_release.py must match the build actually
shipped in the package. APP_VERSION is only ever shown to a human.
"""

APP_VERSION = "3.1.2"
APP_BUILD = 312

# Single source of truth for the package version.
# pyproject.toml reads this via setuptools dynamic `attr`, which parses this file
# statically (no import) only while it stays a plain literal assignment. Do NOT add
# imports or computed logic here, or the PyPI build (which has no NetBox installed)
# will break.
__version__ = "0.1.3"

This script is used to check upstream packages version against what we have in Suse based distribution.

It generates a csv file with the various versions in row.

Requirements:
- python 3.10+
- poetry https://python-poetry.org/docs/
- docker or podman

Usage:
`poetry run src/check.py`
#! /bin/bash
#
# report.sh
#

BASEDIR=$(dirname $0)
cd $BASEDIR
cd ../
poetry run src/check.py
git commit report.csv -m "Update reports $(date --iso-8601=seconds)"
git push

#! /bin/bash
#
# report.sh
#

BASEDIR=$(dirname $0)
cd $BASEDIR
git checkout reports
poetry run src/check.py
git commit report.csv -m "Update reports $(date --iso-8601=seconds)"
git push

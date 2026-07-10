#!/bin/bash
# MD report generation only
set -e
cd "$(dirname "$0")/.."
python3 workflow/report_generator.py

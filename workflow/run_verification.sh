#!/bin/bash
# Mechanics verification only
set -e
cd "$(dirname "$0")/.."
python3 workflow/verify_mechanics.py

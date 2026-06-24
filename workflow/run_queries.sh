#!/bin/bash
# Abstract queries via Hermes only
set -e
cd "$(dirname "$0")/.."
python3 workflow/abstract_queries.py

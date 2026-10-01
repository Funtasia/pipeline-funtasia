#!/bin/sh

set -e

# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install nipple
pip install git+https://github.com/Funtasia/pipeline-funtasia

# Start setup
nipple setup all

#!/bin/bash

set -e

# Create a virtual environment in "venv"
echo "Creating virtual environment..."
python3 -m venv venv

# Activate the virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install packages from requirements.txt
echo "Installing dependencies from requirements.txt..."
pip install -r requirements.txt


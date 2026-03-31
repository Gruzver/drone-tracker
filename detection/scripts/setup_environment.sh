#!/bin/bash

echo "Setting up environment..."

# Crear virtual environment
python -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

echo "✓ Environment setup complete"

#!/bin/bash
# ============================
# Setup script for AI Workshop Assistant PRO
# Ensures Graphviz system binary is installed
# ============================

echo "🔧 Installing system dependencies..."
apt-get update -y && apt-get install -y graphviz

echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "✅ Environment ready!"

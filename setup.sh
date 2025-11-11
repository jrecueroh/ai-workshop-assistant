#!/bin/bash
# ============================
# Setup script for AI Workshop Assistant PRO
# Ensures Graphviz is installed before Streamlit runs
# ============================

echo "🔧 Installing system dependencies..."
apt-get update -y && apt-get install -y graphviz

echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

echo "✅ Environment ready!"

#!/bin/bash

set -e

echo "Let's Start"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# 1. Initialize the virtual environment
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Creating one..."
    python3 -m venv venv || python -m venv venv
else
    echo "Virtual environment already exists. Skipping creation."
fi

# 2. Check System OS & activate venv based on OS
echo "Checking System OS and Activating VENV..."
case "$OSTYPE" in
  msys* | cygwin* | win32*) 
    echo "Windows detected."
    source venv/Scripts/activate
    ;;
  *) 
    echo "Unix-based OS (Linux/macOS) detected."
    source venv/bin/activate
    ;;
esac

echo "Virtual Environment is Active!"

# 3. Install dependencies
echo "Installing/Updating dependencies..."
pip install --upgrade pip
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt 

echo "Setup completed!"

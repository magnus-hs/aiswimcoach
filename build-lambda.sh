#!/bin/bash
# Build the Lambda deployment zip
set -e

cd "$(dirname "$0")"

echo "Cleaning old build..."
rm -rf build/ backend.zip

echo "Installing dependencies..."
mkdir build
pip install -r backend/requirements.txt -t build/ -q

echo "Copying source files..."
cp backend/*.py build/

echo "Creating zip..."
cd build
zip -r ../backend.zip . -q
cd ..

echo "Done! backend.zip created ($(du -h backend.zip | cut -f1))"
rm -rf build/

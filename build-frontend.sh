#!/bin/bash

# Build React frontend
echo "Building React frontend..."
cd frontend

# Install dependencies
npm install

# Build the app
npm run build

# Copy build files to Django static directory
echo "Copying build files to Django static directory..."
mkdir -p ../staticfiles
cp -r build/* ../staticfiles/

echo "Frontend build completed!"

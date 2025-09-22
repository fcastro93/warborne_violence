#!/bin/bash

echo "🧪 Testing Docker build locally..."

# Build the Docker image
echo "📦 Building Docker image..."
docker build -t warborne-tools-test .

if [ $? -eq 0 ]; then
    echo "✅ Docker build successful!"
    echo "🚀 You can test locally with:"
    echo "   docker run -p 80:80 warborne-tools-test"
else
    echo "❌ Docker build failed!"
    exit 1
fi

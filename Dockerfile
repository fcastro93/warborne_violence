FROM python:3.13-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        gcc \
        python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-prod.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables for build
ENV DISABLE_COLLECTSTATIC=1
ENV DEBUG=False
ENV DJANGO_SETTINGS_MODULE=warborne_tools.settings_production

# Copy project
COPY . /app/

# Create logs directory
RUN mkdir -p logs

# Make start script executable
RUN chmod +x start.sh

# Expose port
EXPOSE 8000

# Run the application
CMD ["./start.sh"]

# Use official slim Python image
FROM python:3.12-slim

# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies (needed for compilation or extra packages if any)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt --only-binary=:all:

# Copy codebase
COPY . .

# Expose port
EXPOSE 8000

# Make start script executable
RUN chmod +x start.sh

# Run startup script
CMD ["./start.sh"]

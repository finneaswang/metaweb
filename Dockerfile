# Multi-stage build for MetaWeb with Assignments

# Stage 1: Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies with legacy peer deps
RUN npm install --legacy-peer-deps

# Copy source code
COPY . .

# Build frontend with increased Node memory
ENV NODE_OPTIONS="--max-old-space-size=4096"
RUN npm run build

# Stage 2: Python backend
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements
COPY backend/requirements.txt ./backend/

# Install Python dependencies
RUN pip install --no-cache-dir -r backend/requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Copy CHANGELOG.md to the backend
COPY CHANGELOG.md ./backend/open_webui/

# Copy built frontend from stage 1
COPY --from=frontend-builder /app/build ./build

# Create data directory
RUN mkdir -p /app/data

# Expose port
EXPOSE 8080

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=8080
ENV DATA_DIR=/app/data

# Run the application
CMD ["bash", "backend/start.sh"]

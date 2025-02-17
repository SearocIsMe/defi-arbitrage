FROM python:3.9-slim-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV APP_HOME=/app

# Set work directory
WORKDIR ${APP_HOME}

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install TA-Lib for technical analysis
RUN curl -L https://sourceforge.net/projects/ta-lib/files/ta-lib/0.4.0/ta-lib-0.4.0-src.tar.gz/download | tar xzf - \
    && cd ta-lib \
    && ./configure --prefix=/usr \
    && make \
    && make install \
    && cd .. \
    && rm -rf ta-lib

# Copy project files
COPY . ${APP_HOME}

# Install Python dependencies
COPY requirements.txt ${APP_HOME}/
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install ta-lib

# Create necessary directories
RUN mkdir -p /app/logs \
    && mkdir -p /app/monitoring

# Copy configuration files
COPY .env.example /app/.env
COPY monitoring/prometheus.yml /app/monitoring/
COPY monitoring/alerts.yml /app/monitoring/

# Set permissions
RUN chmod +x /app/arbitrage_detector.py

# Expose metrics port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=5m --timeout=3s \
  CMD curl -f http://localhost:8000/health || exit 1

# Run the application
ENTRYPOINT ["python", "arbitrage_detector.py"]

# Default arguments can be overridden
CMD ["--config", "/app/.env"]
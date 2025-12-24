FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install build dependencies for some Python packages (bcrypt, lxml, etc.)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential gcc libffi-dev libssl-dev libxml2-dev libxslt1-dev && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --upgrade pip && pip install --no-cache-dir -r /app/requirements.txt

# Copy project
COPY . /app

EXPOSE 5000

# Default command — runs the local runner which starts the Flask app
CMD ["python", "run_local.py"]

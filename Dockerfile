# Use Python 3.10
FROM python:3.10-slim

# Install build dependencies (for psutil, etc.) + any needed dev libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    libffi-dev \
    libssl-dev \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy your requirements, then install them
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy in the rest of your source/data
COPY . /app/

# Expose port 8888 (Jupyter's default)
EXPOSE 8888

# Automatically launch Jupyter Lab when the container starts.
# --ip=0.0.0.0  : Bind to all interfaces (needed for Docker port-forward).
# --allow-root  : Run as root inside container.
# --no-browser  : Don’t open a browser in Docker console.
CMD ["jupyter", "lab", "--ip=0.0.0.0", "--allow-root", "--no-browser"]
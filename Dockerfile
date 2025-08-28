# Use a lightweight base image
FROM python:3.10-slim

# Set up a working directory
WORKDIR /app

# Install system dependencies required by OpenCV
RUN apt-get update -o Acquire::Retries=3 \
 && apt-get install -y --no-install-recommends \
      libgl1 \
      libglib2.0-0 \
 && rm -rf /var/lib/apt/lists/*

# Install the package from PyPI
RUN python -m pip install --upgrade pip \
 && pip install --pre alpss

# Set a default command (optional)
CMD ["/bin/bash"]

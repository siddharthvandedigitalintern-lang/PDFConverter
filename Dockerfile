# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Install system dependencies required by WeasyPrint and font configuration
RUN apt-get update && apt-get install -y \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    python3-cffi-backend \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-liberation \
    fontconfig \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the current directory contents into the container at /app
COPY . .

# Expose port 10000 for the Render service
EXPOSE 10000

# Run gunicorn when the container launches
CMD ["gunicorn", "--bind", "0.0.0.0:10000", "app:app"]

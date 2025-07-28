# Use explicit platform specification
FROM --platform=linux/amd64 python:3.9-slim-buster

# Set the working directory inside the container
WORKDIR /app

ENV PYTHONPATH /app

# Copy requirements.txt and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire source code into the container
COPY src/ ./src/
COPY models/ ./models/

# Ensure output directory exists
RUN mkdir -p /app/output

# Command to run the application
CMD ["python", "-m", "src.main"]
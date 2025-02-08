# Use the official Python slim image.
FROM python:3.9-slim

# Prevent Python from writing .pyc files and enable output buffering.
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory.
WORKDIR /app

# Copy requirements and install them.
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the rest of the application code.
COPY . .

# Expose the port Cloud Run will use.
EXPOSE 8080

# Run the application.
CMD ["python", "app.py"]

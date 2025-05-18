# Use official Python image
FROM python:3.13-slim

# Set environment vars
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Create work directory
WORKDIR /app

# Install Poetry
RUN pip install poetry
COPY pyproject.toml poetry.lock* /app/

# Install dependencies
RUN poetry config virtualenvs.create false \
 && poetry install --no-root --only main

# Copy remaining code
COPY . /app/

EXPOSE 8002

# Run the app
CMD ["gunicorn ", "--bind", "0.0.0.0:8002", "dogfood.wsgi", "-w", "4"]
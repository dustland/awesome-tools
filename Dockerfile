FROM python:3.11-slim

# Set environment variables
ENV PYTHONFAULTHANDLER=1 \
  PYTHONUNBUFFERED=1 \
  PYTHONDONTWRITEBYTECODE=1 \
  PIP_NO_CACHE_DIR=1 \
  PIP_DISABLE_PIP_VERSION_CHECK=1 \
  POETRY_VERSION=1.7.1 \
  POETRY_NO_INTERACTION=1 \
  POETRY_VIRTUALENVS_CREATE=false \
  POETRY_HOME="/opt/poetry" \
  PYTHONPATH=/app/src \
  PATH="/opt/poetry/bin:$PATH"

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  git \
  && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN curl -sSL https://install.python-poetry.org | POETRY_HOME=/opt/poetry python3 - && \
  chmod a+x /opt/poetry/bin/poetry

# Copy only the necessary files first
COPY pyproject.toml poetry.lock ./

# Create src directory structure
RUN mkdir -p src/awesome_updater src/utils src/models

# Install dependencies and install the package in development mode
RUN poetry install --no-dev && \
  poetry install

# Copy the rest of the application
COPY . .

# Initialize Git repository and configure Git
RUN git init && \
  git config --global user.email "bot@dustland.ai" && \
  git config --global user.name "Dustland Bot"

# Command to run the script
CMD ["poetry", "run", "python", "-m", "awesome_updater.main"] 
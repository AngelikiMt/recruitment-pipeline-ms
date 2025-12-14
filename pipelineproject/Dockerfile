FROM python:3.12-slim

# Prevents Python from writing pyc files
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Goes to the app directory
WORKDIR /app

# System dependencies for psycopg2
RUN apt-get update \
    && apt-get install -y gcc libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .

# Install app dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# PORT
EXPOSE 8000

# Run the app
CMD ["gunicorn", "pipelineproject.wsgi:application", "--bind", "0.0.0.0:8000"]

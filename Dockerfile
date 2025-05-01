FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    DJANGO_RUNNING_IN_DOCKER=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libgirepository1.0-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    shared-mime-info \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data/new_files /app/data/processed

VOLUME /app/data

CMD ["sh", "-c", "sleep 5 && \
                python manage.py makemigrations && \
                python manage.py migrate && \
                python manage.py runserver"]
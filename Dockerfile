FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs reports database

EXPOSE 8000 8501

ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py", "--mode", "all"]

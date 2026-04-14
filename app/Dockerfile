FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY webhook_receiver.py .

RUN adduser --disabled-password --no-create-home appuser
USER appuser

CMD ["uvicorn", "webhook_receiver:app", "--host", "0.0.0.0", "--port", "8000"]

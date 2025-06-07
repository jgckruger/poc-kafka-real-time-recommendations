FROM python:3.11-slim
WORKDIR /app
COPY main.py .
RUN pip install aiokafka prometheus_client valkey
CMD ["python", "main.py"]

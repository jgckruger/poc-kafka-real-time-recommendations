FROM python:3.11-slim
WORKDIR /app
COPY event_gen.py .
RUN pip install aiokafka
CMD ["python", "event_gen.py"]

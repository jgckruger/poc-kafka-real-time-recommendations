# Real-Time Recommendation PoC

This project demonstrates a scalable, production-structured real-time recommendation system using Python, Kafka, Valkey, and Prometheus, with microservices for popularity, item-to-item similarity, and user recommendations.

## Features

- **Kafka (Redpanda compatible)** for event streaming
- **Valkey** for stateful online storage (ZSETs, HASH)
- **Microservice architecture** (Docker Compose)
- **Prometheus metrics** in every service
- **FastAPI gateway** exposing recommendation endpoints
- **Configurable & horizontally scalable** (`docker compose up --scale ...`)
- **Structured JSON logging**
- **Synthetic event generator**

---

## Folder Structure

```
realtime-rec/
├─ docker-compose.yml
├─ kafka-init/ (script to create topic)
├─ event-gen/ (synthetic event generator)
├─ popularity-svc/
├─ item-sim-svc/
├─ user-rec-svc/
└─ api-gateway/
```

---

## 1. Start the Stack

### 1.1. Build and launch everything:

```bash
docker compose up -d --build
```

### 1.2. Create the Kafka topic:

Kafka topics are now created automatically when the stack starts. No manual step is needed.

### 1.3. Kafka Web UI

A web UI for Kafka is available at [http://localhost:8080](http://localhost:8080) (Kafka UI by Provectus). Use it to browse topics, messages, and consumer groups.

---

## 2. Generate Synthetic Events

To fill the system with test data, run:

```bash
docker compose run --rm event-gen
```

This will stream random user play events to Kafka.

---

## 3. Test the Endpoints

### 3.1. Popularity
Get the global most popular content:

```bash
curl http://localhost:8000/recommendations/popularity
```

Sample Response:

```json
{
  "top": [
    {"content_id": "item_12", "score": 55},
    {"content_id": "item_23", "score": 48}
  ]
}
```

### 3.2. Content-to-Content (Item Similarity)
Get items most co-watched with a given item:

```bash
curl http://localhost:8000/recommendations/content/item_12
```

Sample Response:

```json
{
  "content_id": "item_12",
  "similar": [
    {"content_id": "item_23", "score": 21},
    {"content_id": "item_77", "score": 18}
  ]
}
```

### 3.3. User Recommendations
Get tailored recs for a user:

```bash
curl http://localhost:8000/recommendations/user/user_1
```

Sample Response:

```json
{
  "user_id": "user_1",
  "recommendations": [
    {"content_id": "item_44", "score": 9},
    {"content_id": "item_6", "score": 6}
  ]
}
```

---

## 4. Prometheus Metrics

Each service exposes metrics at `/metrics` (default ports 9001/9002/9003). Example:

```bash
curl http://localhost:9001/metrics
```

---

## 5. Scaling & Notes

Scale any consumer:

```bash
docker compose up --scale popularity-svc=3
```

To cluster Valkey or use for prod:
Swap the service in `docker-compose.yml` for K8s or Docker Swarm (see comments in the file).

---

## 6. Configuration

All config is via environment variables:

- `KAFKA_BOOTSTRAP_SERVERS`
- `VALKEY_HOST`
- `VALKEY_PORT`
- `KAFKA_TOPIC`

---

## 7. Logging

All services use JSON structured logs for production readiness.

---

## 8. Troubleshooting

- Ensure all containers are up (`docker ps`)
- See logs: `docker compose logs -f <service>`
- If you need to reset Valkey, run `docker compose down -v` then `up -d --build`

---

Happy hacking!
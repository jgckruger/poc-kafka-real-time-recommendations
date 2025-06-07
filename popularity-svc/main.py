import os, asyncio, json, time, logging
from aiokafka import AIOKafkaConsumer
import valkey
from prometheus_client import start_http_server, Counter, Gauge, Histogram, Summary

logging.basicConfig(level="INFO", format='%(message)s')
logger = logging.getLogger("popularity-svc")

KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'user_actions')
VALKEY_HOST = os.getenv('VALKEY_HOST', 'valkey')
VALKEY_PORT = int(os.getenv('VALKEY_PORT', 6379))
PROM_PORT = int(os.getenv('PROM_PORT', 9001))
CONSUMER_GROUP = "popularity-svc"

EVENTS_PROCESSED = Counter('popularity_events_processed', 'Events processed')
PROCESSING_LATENCY = Histogram('popularity_processing_latency_seconds', 'Event processing latency')
KAFKA_LAG = Gauge('popularity_kafka_lag', 'Consumer lag')

def json_log(msg, **kwargs):
    logger.info(json.dumps(dict(msg=msg, **kwargs)))

async def main():
    start_http_server(PROM_PORT)
    client = valkey.Valkey(host=VALKEY_HOST, port=VALKEY_PORT, socket_timeout=3)
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=CONSUMER_GROUP,
        enable_auto_commit=True,
        auto_offset_reset="earliest",
        value_deserializer=lambda x: json.loads(x.decode()),
        max_poll_records=10
    )
    await consumer.start()
    json_log("Started consumer", svc="popularity", group=CONSUMER_GROUP)
    try:
        while True:
            batch = await consumer.getmany(timeout_ms=1000)
            for tp, messages in batch.items():
                partitions_lag = consumer.highwater(tp) - await consumer.position(tp)
                KAFKA_LAG.set(partitions_lag)
                for msg in messages:
                    ts1 = time.time()
                    evt = msg.value
                    content_id = evt.get("content_id")
                    if not content_id:
                        continue
                    try:
                        client.zincrby("popularity", 1, content_id)
                        EVENTS_PROCESSED.inc()
                        latency = time.time() - ts1
                        PROCESSING_LATENCY.observe(latency)
                        json_log("popularity_updated", content_id=content_id, latency=latency)
                    except Exception as e:
                        json_log("valkey_err", error=str(e))
                        await asyncio.sleep(2)
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(main())

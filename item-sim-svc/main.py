import os, asyncio, json, time, logging
from aiokafka import AIOKafkaConsumer
import valkey
from prometheus_client import start_http_server, Counter, Gauge, Histogram

logging.basicConfig(level="INFO", format='%(message)s')
logger = logging.getLogger("item-sim-svc")

KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'user_actions')
VALKEY_HOST = os.getenv('VALKEY_HOST', 'valkey')
VALKEY_PORT = int(os.getenv('VALKEY_PORT', 6379))
PROM_PORT = int(os.getenv('PROM_PORT', 9002))
CONSUMER_GROUP = "item-sim-svc"

EVENTS_PROCESSED = Counter('sim_events_processed', 'Events processed')
PROCESSING_LATENCY = Histogram('sim_processing_latency_seconds', 'Event processing latency')
KAFKA_LAG = Gauge('sim_kafka_lag', 'Consumer lag')

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
    user_last_items = dict()
    json_log("Started consumer", svc="item-sim")
    try:
        while True:
            batch = await consumer.getmany(timeout_ms=1000)
            for tp, messages in batch.items():
                partitions_lag = consumer.highwater(tp) - consumer.position(tp)
                KAFKA_LAG.set(partitions_lag)
                for msg in messages:
                    ts1 = time.time()
                    evt = msg.value
                    uid = evt.get("user_id")
                    content_id = evt.get("content_id")
                    if not uid or not content_id:
                        continue
                    prev_item = user_last_items.get(uid)
                    if prev_item and prev_item != content_id:
                        # Increment co-watch count both ways
                        try:
                            client.zincrby(f"sim:{prev_item}", 1, content_id)
                            client.zincrby(f"sim:{content_id}", 1, prev_item)
                        except Exception as e:
                            json_log("valkey_err", error=str(e))
                            await asyncio.sleep(2)
                    user_last_items[uid] = content_id
                    EVENTS_PROCESSED.inc()
                    latency = time.time() - ts1
                    PROCESSING_LATENCY.observe(latency)
                    json_log("item_sim_update", user_id=uid, content_id=content_id, latency=latency)
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(main())

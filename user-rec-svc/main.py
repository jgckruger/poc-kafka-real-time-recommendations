import os, asyncio, json, time, logging
from aiokafka import AIOKafkaConsumer
import valkey
from prometheus_client import start_http_server, Counter, Gauge, Histogram

logging.basicConfig(level="INFO", format='%(message)s')
logger = logging.getLogger("user-rec-svc")

KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'user_actions')
VALKEY_HOST = os.getenv('VALKEY_HOST', 'valkey')
VALKEY_PORT = int(os.getenv('VALKEY_PORT', 6379))
PROM_PORT = int(os.getenv('PROM_PORT', 9003))
CONSUMER_GROUP = "user-rec-svc"

EVENTS_PROCESSED = Counter('user_rec_events_processed', 'Events processed')
PROCESSING_LATENCY = Histogram('user_rec_processing_latency_seconds', 'Event processing latency')
KAFKA_LAG = Gauge('user_rec_kafka_lag', 'Consumer lag')

def json_log(msg, **kwargs):
    logger.info(json.dumps(dict(msg=msg, **kwargs)))

async def get_user_recommendations(client, uid, recs_per_item=5, history_len=20):
    # Get user's recent history
    history = client.lrange(f"profile:{uid}", 0, history_len-1)
    if not history:
        return []
    rec_scores = {}
    seen = set(history)
    for item in history:
        # For each item, get top N similar items from Valkey (with scores)
        similar = client.zrevrange(f"sim:{item}", 0, recs_per_item-1, withscores=True)
        for sim_item, score in similar:
            if sim_item not in seen:
                rec_scores[sim_item] = rec_scores.get(sim_item, 0) + score
                seen.add(sim_item)
    # Sort by total score descending
    recs = [item for item, _ in sorted(rec_scores.items(), key=lambda x: -x[1])]
    return recs

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
    json_log("Started consumer", svc="user-rec")
    try:
        while True:
            batch = await consumer.getmany(timeout_ms=1000)
            for tp, messages in batch.items():
                partitions_lag = consumer.highwater(tp) - await consumer.position(tp)
                KAFKA_LAG.set(partitions_lag)
                for msg in messages:
                    ts1 = time.time()
                    evt = msg.value
                    uid = evt.get("user_id")
                    content_id = evt.get("content_id")
                    if not uid or not content_id:
                        continue
                    try:
                        # Track last N items per user (store as a Valkey list)
                        client.lpush(f"profile:{uid}", content_id)
                        client.ltrim(f"profile:{uid}", 0, 19)  # keep last 20
                        # Compute recommendations and store in Valkey
                        recs = await get_user_recommendations(client, uid)
                        client.set(f"userrecs:{uid}", json.dumps(recs))
                        EVENTS_PROCESSED.inc()
                        latency = time.time() - ts1
                        PROCESSING_LATENCY.observe(latency)
                        json_log("user_profile_updated", user_id=uid, content_id=content_id, recommendations=recs, latency=latency)
                    except Exception as e:
                        json_log("valkey_err", error=str(e))
                        await asyncio.sleep(2)
    finally:
        await consumer.stop()

if __name__ == "__main__":
    asyncio.run(main())

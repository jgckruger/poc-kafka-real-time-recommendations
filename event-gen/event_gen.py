import os
import json
import random
import time
import asyncio
from aiokafka import AIOKafkaProducer

KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
KAFKA_TOPIC = os.getenv('KAFKA_TOPIC', 'user_actions')

USERS = [f"user_{i}" for i in range(1, 21)]
ITEMS = [f"item_{i}" for i in range(1, 51)]

async def produce_events():
    producer = AIOKafkaProducer(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)
    await producer.start()
    try:
        while True:
            evt = {
                "user_id": random.choice(USERS),
                "content_id": random.choice(ITEMS),
                "event_type": "play",
                "ts": int(time.time())
            }
            await producer.send_and_wait(KAFKA_TOPIC, json.dumps(evt).encode())
            print(json.dumps(evt))
            await asyncio.sleep(random.uniform(0.05, 0.2))
    finally:
        await producer.stop()

if __name__ == "__main__":
    asyncio.run(produce_events())

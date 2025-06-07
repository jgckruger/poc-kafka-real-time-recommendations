#!/bin/bash
set -e

KAFKA_TOPICS="user_actions"
BOOTSTRAP_SERVERS=${KAFKA_BOOTSTRAP_SERVERS:-kafka:9092}

echo "Creating Kafka topics..."
/opt/bitnami/kafka/bin/kafka-topics.sh --create --if-not-exists \
    --bootstrap-server $BOOTSTRAP_SERVERS \
    --replication-factor 1 \
    --partitions 3 \
    --topic $KAFKA_TOPICS

echo "Done."
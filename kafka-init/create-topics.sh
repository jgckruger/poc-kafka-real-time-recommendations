#!/bin/bash
set -e

# Determine the correct bootstrap server based on how the script is run
if [[ $(hostname) == "kafka" ]]; then
  BOOTSTRAP_SERVER="kafka:9092"
else
  BOOTSTRAP_SERVER="localhost:9092"
fi

KAFKA_TOPICS="user_actions"

echo "Creating Kafka topics..."
/opt/bitnami/kafka/bin/kafka-topics.sh --create --if-not-exists \
    --bootstrap-server $BOOTSTRAP_SERVER \
    --replication-factor 1 \
    --partitions 3 \
    --topic $KAFKA_TOPICS

echo "Done."
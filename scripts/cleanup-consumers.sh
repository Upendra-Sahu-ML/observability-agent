#!/bin/bash

# Get all stream names
streams=$(nats stream ls --names)

for stream in $streams; do
  echo "📦 Processing stream: $stream"
  
  # Get all consumer names for this stream
  consumers=$(nats consumer ls "$stream" --names)

  for consumer in $consumers; do
    echo "❌ Deleting consumer '$consumer' from stream '$stream'"
    nats consumer delete "$stream" "$consumer"
  done
done

# List all streams
nats stream ls

# Purge each stream
for stream in $(nats stream ls -n); do
  echo "Purging stream: $stream"
  nats stream purge $stream --force
done
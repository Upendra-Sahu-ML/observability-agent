# List all streams
nats stream ls

# Purge each stream
for stream in $(nats stream ls -n); do
  echo "Deleting stream: $stream"
  nats stream rm "$stream" --force
done
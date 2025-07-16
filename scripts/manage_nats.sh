#!/bin/bash

# NATS Stream Management Script
# Consolidated script for managing NATS streams and consumers

set -e

NATS_URL=${NATS_URL:-"nats://localhost:4222"}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
    echo "Usage: $0 [cleanup|delete|purge|info] [options]"
    echo ""
    echo "Commands:"
    echo "  cleanup    - Remove all consumers but keep streams"
    echo "  delete     - Delete all streams"
    echo "  purge      - Purge all data from streams"
    echo "  info       - Show stream information"
    echo ""
    echo "Options:"
    echo "  --nats-url=<url>  NATS server URL (default: nats://localhost:4222)"
    echo "  --stream=<name>   Target specific stream (default: all)"
    echo ""
    echo "Examples:"
    echo "  $0 cleanup"
    echo "  $0 delete --stream=METRICS"
    echo "  $0 purge --nats-url=nats://remote:4222"
}

# Parse arguments
COMMAND=""
STREAM=""
while [[ $# -gt 0 ]]; do
    case $1 in
        cleanup|delete|purge|info)
            COMMAND="$1"
            shift
            ;;
        --nats-url=*)
            NATS_URL="${1#*=}"
            shift
            ;;
        --stream=*)
            STREAM="${1#*=}"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

if [[ -z "$COMMAND" ]]; then
    echo "Error: Command required"
    usage
    exit 1
fi

# Common streams
STREAMS=(
    "METRICS"
    "LOGS"
    "ALERTS"
    "DEPLOYMENTS"
    "AGENT_STATUS"
    "TRACES"
    "NOTIFICATIONS"
    "POSTMORTEMS"
    "RUNBOOKS"
    "RUNBOOK_EXECUTIONS"
    "ROOT_CAUSES"
    "KNOWLEDGE_BASE"
)

# Functions
cleanup_consumers() {
    echo "Cleaning up consumers..."
    for stream in "${STREAMS[@]}"; do
        if [[ -n "$STREAM" && "$stream" != "$STREAM" ]]; then
            continue
        fi
        
        echo "Cleaning consumers for stream: $stream"
        nats consumer list --server="$NATS_URL" "$stream" 2>/dev/null | grep -E "^  [a-zA-Z]" | while read -r consumer; do
            consumer_name=$(echo "$consumer" | awk '{print $1}')
            echo "  Removing consumer: $consumer_name"
            nats consumer rm --server="$NATS_URL" "$stream" "$consumer_name" --force 2>/dev/null || echo "    Consumer not found or already removed"
        done
    done
}

delete_streams() {
    echo "Deleting streams..."
    for stream in "${STREAMS[@]}"; do
        if [[ -n "$STREAM" && "$stream" != "$STREAM" ]]; then
            continue
        fi
        
        echo "Deleting stream: $stream"
        nats stream rm --server="$NATS_URL" "$stream" --force 2>/dev/null || echo "  Stream not found or already deleted"
    done
}

purge_streams() {
    echo "Purging streams..."
    for stream in "${STREAMS[@]}"; do
        if [[ -n "$STREAM" && "$stream" != "$STREAM" ]]; then
            continue
        fi
        
        echo "Purging stream: $stream"
        nats stream purge --server="$NATS_URL" "$stream" --force 2>/dev/null || echo "  Stream not found or already purged"
    done
}

show_info() {
    echo "Stream information:"
    echo "NATS URL: $NATS_URL"
    echo ""
    
    for stream in "${STREAMS[@]}"; do
        if [[ -n "$STREAM" && "$stream" != "$STREAM" ]]; then
            continue
        fi
        
        echo "=== Stream: $stream ==="
        nats stream info --server="$NATS_URL" "$stream" 2>/dev/null || echo "  Stream not found"
        echo ""
    done
}

# Execute command
case $COMMAND in
    cleanup)
        cleanup_consumers
        ;;
    delete)
        cleanup_consumers
        delete_streams
        ;;
    purge)
        purge_streams
        ;;
    info)
        show_info
        ;;
    *)
        echo "Unknown command: $COMMAND"
        usage
        exit 1
        ;;
esac

echo "Operation completed successfully!"
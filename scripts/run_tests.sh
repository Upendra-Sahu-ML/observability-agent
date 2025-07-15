#!/bin/bash

# Test Runner Script for Observability Agent
# Simplified script to run all Python-based tests and utilities

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Default values
NATS_URL="nats://localhost:4222"
PYTHON_CMD="python3"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_usage() {
    cat << EOF
Usage: $0 [COMMAND] [OPTIONS]

Commands:
    setup       - Setup NATS streams for testing
    generate    - Generate test data
    test        - Run system tests
    health      - Check system health
    clean       - Clean up test data
    help        - Show this help message

Options:
    --nats-url=<url>    NATS server URL (default: nats://localhost:4222)
    --python=<cmd>      Python command to use (default: python3)
    --count=<n>         Number of test items to generate (default: 50)
    --type=<type>       Type of data to generate (alerts|metrics|logs|deployments|agents|all)

Examples:
    $0 setup
    $0 generate --type=alerts --count=10
    $0 test
    $0 health --nats-url=nats://remote:4222

EOF
}

check_dependencies() {
    echo -e "${YELLOW}Checking dependencies...${NC}"
    
    # Check Python
    if ! command -v $PYTHON_CMD &> /dev/null; then
        echo -e "${RED}Error: $PYTHON_CMD not found${NC}"
        exit 1
    fi
    
    # Check if nats-py is installed
    if ! $PYTHON_CMD -c "import nats" &> /dev/null; then
        echo -e "${YELLOW}Installing nats-py...${NC}"
        pip install nats-py
    fi
    
    echo -e "${GREEN}Dependencies checked successfully${NC}"
}

setup_streams() {
    echo -e "${BLUE}Setting up NATS streams...${NC}"
    $PYTHON_CMD "${SCRIPT_DIR}/nats_utils.py" --nats-url="$NATS_URL" setup
}

generate_test_data() {
    local data_type="all"
    local count=50
    
    # Parse additional arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --type=*)
                data_type="${1#*=}"
                shift
                ;;
            --count=*)
                count="${1#*=}"
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    echo -e "${BLUE}Generating test data (type: $data_type, count: $count)...${NC}"
    $PYTHON_CMD "${SCRIPT_DIR}/generate_test_data.py" --nats-url="$NATS_URL" --type="$data_type" --count="$count"
}

run_tests() {
    echo -e "${BLUE}Running system tests...${NC}"
    $PYTHON_CMD "${SCRIPT_DIR}/test_system.py" --nats-url="$NATS_URL"
}

check_health() {
    echo -e "${BLUE}Checking system health...${NC}"
    $PYTHON_CMD "${SCRIPT_DIR}/nats_utils.py" --nats-url="$NATS_URL" health
}

clean_test_data() {
    echo -e "${BLUE}Cleaning up test data...${NC}"
    
    # List of test streams to purge
    test_streams=("ALERTS" "METRICS" "LOGS" "DEPLOYMENTS" "AGENTS" "RUNBOOKS" "NOTIFICATIONS" "ROOT_CAUSE")
    
    for stream in "${test_streams[@]}"; do
        echo -e "${YELLOW}Purging stream: $stream${NC}"
        $PYTHON_CMD "${SCRIPT_DIR}/nats_utils.py" --nats-url="$NATS_URL" purge --stream="$stream"
    done
    
    echo -e "${GREEN}Test data cleaned successfully${NC}"
}

run_full_test_suite() {
    echo -e "${GREEN}Running full test suite...${NC}"
    echo -e "${YELLOW}This will setup streams, generate data, and run tests${NC}"
    echo
    
    setup_streams
    echo
    
    generate_test_data --type=all --count=20
    echo
    
    run_tests
    echo
    
    check_health
    echo
    
    echo -e "${GREEN}Full test suite completed!${NC}"
}

# Parse command line arguments
COMMAND=""
while [[ $# -gt 0 ]]; do
    case $1 in
        setup|generate|test|health|clean|full|help)
            COMMAND=$1
            shift
            ;;
        --nats-url=*)
            NATS_URL="${1#*=}"
            shift
            ;;
        --python=*)
            PYTHON_CMD="${1#*=}"
            shift
            ;;
        *)
            # Pass through other arguments
            break
            ;;
    esac
done

# Show usage if no command provided
if [[ -z "$COMMAND" ]]; then
    print_usage
    exit 1
fi

# Check dependencies before running any command
check_dependencies

# Execute the requested command
case $COMMAND in
    setup)
        setup_streams
        ;;
    generate)
        generate_test_data "$@"
        ;;
    test)
        run_tests
        ;;
    health)
        check_health
        ;;
    clean)
        clean_test_data
        ;;
    full)
        run_full_test_suite
        ;;
    help)
        print_usage
        ;;
    *)
        echo -e "${RED}Unknown command: $COMMAND${NC}"
        print_usage
        exit 1
        ;;
esac
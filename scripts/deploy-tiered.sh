#!/bin/bash

# Tiered Deployment Script for Observability Agent
# Supports basic, standard, and advanced deployment modes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
HELM_DIR="${PROJECT_DIR}/helm/observability-agent"

# Default values
MODE="standard"
NAMESPACE="observability"
RELEASE_NAME="observability-agent"
OPENAI_API_KEY=""
DRY_RUN=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy Observability Agent in different modes:

MODES:
    basic     - Minimal runbook execution (1Gi memory, basic K8s integration)
    standard  - Full observability integration (3Gi memory, Prometheus + Loki)
    advanced  - Full feature set (current complex deployment)

OPTIONS:
    -m, --mode MODE           Deployment mode (basic|standard|advanced) [default: standard]
    -n, --namespace NAMESPACE Kubernetes namespace [default: observability]
    -r, --release RELEASE     Helm release name [default: observability-agent]
    -k, --api-key KEY         OpenAI API key (required)
    --dry-run                 Show what would be deployed without actually deploying
    -h, --help                Show this help message

EXAMPLES:
    # Deploy basic mode for small teams
    $0 --mode basic --api-key sk-...

    # Deploy standard mode with observability
    $0 --mode standard --api-key sk-... --namespace obs

    # Dry run to see what would be deployed
    $0 --mode standard --api-key sk-... --dry-run

EOF
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -m|--mode)
                MODE="$2"
                shift 2
                ;;
            -n|--namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            -r|--release)
                RELEASE_NAME="$2"
                shift 2
                ;;
            -k|--api-key)
                OPENAI_API_KEY="$2"
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            -h|--help)
                print_usage
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done
}

validate_args() {
    if [[ -z "$OPENAI_API_KEY" ]]; then
        echo -e "${RED}Error: OpenAI API key is required${NC}"
        echo "Use: $0 --api-key sk-your-key-here"
        exit 1
    fi

    if [[ ! "$MODE" =~ ^(basic|standard|advanced)$ ]]; then
        echo -e "${RED}Error: Invalid mode '$MODE'. Must be basic, standard, or advanced${NC}"
        exit 1
    fi
}

check_prerequisites() {
    echo -e "${YELLOW}Checking prerequisites...${NC}"

    # Check kubectl
    if ! command -v kubectl &> /dev/null; then
        echo -e "${RED}Error: kubectl not found${NC}"
        exit 1
    fi

    # Check helm
    if ! command -v helm &> /dev/null; then
        echo -e "${RED}Error: helm not found${NC}"
        exit 1
    fi

    # Check kubernetes connection
    if ! kubectl cluster-info &> /dev/null; then
        echo -e "${RED}Error: Cannot connect to Kubernetes cluster${NC}"
        exit 1
    fi

    echo -e "${GREEN}Prerequisites checked successfully${NC}"
}

create_namespace() {
    echo -e "${YELLOW}Creating namespace '$NAMESPACE'...${NC}"
    kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
}

deploy_basic_mode() {
    echo -e "${YELLOW}Deploying in BASIC mode...${NC}"
    echo "  - Minimal observability (kubectl fallbacks)"
    echo "  - Core runbook execution"
    echo "  - Resource usage: ~1Gi memory, ~500m CPU"
    
    local values_file="${HELM_DIR}/values-basic.yaml"
    local helm_args=(
        upgrade --install "$RELEASE_NAME" "$HELM_DIR"
        --namespace "$NAMESPACE"
        --values "$values_file"
        --set openai.apiKey="$OPENAI_API_KEY"
        --set deployment.mode="basic"
    )

    if [[ "$DRY_RUN" == "true" ]]; then
        helm_args+=(--dry-run)
        echo -e "${YELLOW}DRY RUN: Would execute:${NC}"
        echo "helm ${helm_args[*]}"
    fi

    helm "${helm_args[@]}"
}

deploy_standard_mode() {
    echo -e "${YELLOW}Deploying in STANDARD mode...${NC}"
    echo "  - Full observability integration (Prometheus + Loki)"
    echo "  - Intelligent runbook selection"
    echo "  - Resource usage: ~3Gi memory, ~2000m CPU"
    
    local values_file="${HELM_DIR}/values-standard.yaml"
    local helm_args=(
        upgrade --install "$RELEASE_NAME" "$HELM_DIR"
        --namespace "$NAMESPACE"
        --values "$values_file"
        --set openai.apiKey="$OPENAI_API_KEY"
        --set deployment.mode="standard"
    )

    if [[ "$DRY_RUN" == "true" ]]; then
        helm_args+=(--dry-run)
        echo -e "${YELLOW}DRY RUN: Would execute:${NC}"
        echo "helm ${helm_args[*]}"
    fi

    helm "${helm_args[@]}"
}

deploy_advanced_mode() {
    echo -e "${YELLOW}Deploying in ADVANCED mode...${NC}"
    echo "  - Full feature set (all agents, all integrations)"
    echo "  - Maximum observability (Prometheus + Loki + Tempo)"
    echo "  - Resource usage: ~5Gi memory, ~3000m CPU"
    
    local helm_args=(
        upgrade --install "$RELEASE_NAME" "$HELM_DIR"
        --namespace "$NAMESPACE"
        --set openai.apiKey="$OPENAI_API_KEY"
        --set deployment.mode="advanced"
    )

    if [[ "$DRY_RUN" == "true" ]]; then
        helm_args+=(--dry-run)
        echo -e "${YELLOW}DRY RUN: Would execute:${NC}"
        echo "helm ${helm_args[*]}"
    fi

    helm "${helm_args[@]}"
}

show_deployment_info() {
    if [[ "$DRY_RUN" == "true" ]]; then
        return
    fi

    echo -e "${GREEN}Deployment completed successfully!${NC}"
    echo
    echo "To check the status:"
    echo "  kubectl get pods -n $NAMESPACE"
    echo
    echo "To access the UI:"
    echo "  kubectl port-forward -n $NAMESPACE svc/$RELEASE_NAME-ui 8080:80"
    echo "  Then open http://localhost:8080"
    echo
    echo "To access the API:"
    echo "  kubectl port-forward -n $NAMESPACE svc/$RELEASE_NAME-unified-backend 5000:5000"
    echo "  Then use http://localhost:5000/api"
    echo
    echo "To view logs:"
    echo "  kubectl logs -n $NAMESPACE -l app.kubernetes.io/name=observability-agent"
}

main() {
    parse_args "$@"
    validate_args
    check_prerequisites
    
    echo -e "${GREEN}Starting Observability Agent deployment...${NC}"
    echo "Mode: $MODE"
    echo "Namespace: $NAMESPACE"
    echo "Release: $RELEASE_NAME"
    echo

    create_namespace

    case "$MODE" in
        basic)
            deploy_basic_mode
            ;;
        standard)
            deploy_standard_mode
            ;;
        advanced)
            deploy_advanced_mode
            ;;
    esac

    show_deployment_info
}

main "$@"
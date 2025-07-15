# Makefile for building and deploying the Observability Agent system

# Set the container command - use podman if available, otherwise docker
CONTAINER_CMD ?= $(shell which podman 2>/dev/null || which docker 2>/dev/null || echo docker)

# Set the compose command based on container command
ifeq ($(shell basename $(CONTAINER_CMD)),podman)
    COMPOSE_CMD ?= podman-compose
else
    COMPOSE_CMD ?= docker-compose
endif

# Default values
REGISTRY ?= localhost:5000
TAG ?= latest
NAMESPACE ?= observability
RELEASE_NAME ?= observability-agent
PROMETHEUS_URL ?= http://prometheus-server.monitoring:9090
LOKI_URL ?= http://loki-gateway.monitoring:3100
PLATFORM ?= linux/amd64

# List of components to build
COMPONENTS = orchestrator observability-agent infrastructure-agent communication-agent root-cause-agent unified-backend ui

# Additional tools
TOOLS = alert-publisher

.PHONY: all build push deploy clean help $(COMPONENTS) $(TOOLS)

# Default target
all: build

# Help information
help:
	@echo "Observability Agent Makefile"
	@echo "----------------------------"
	@echo "Available targets:"
	@echo "  build        : Build all container images"
	@echo "  push         : Push all container images to registry"
	@echo "  deploy       : Deploy the Helm chart"
	@echo "  clean        : Remove all container images"
	@echo "  help         : Show this help message"
	@echo ""
	@echo "Individual component targets:"
	@echo "  orchestrator     : Build the Orchestrator image"
	@echo "  observability-agent : Build the Consolidated Observability Agent image"
	@echo "  infrastructure-agent : Build the Consolidated Infrastructure Agent image"
	@echo "  communication-agent : Build the Consolidated Communication Agent image"
	@echo "  root-cause-agent : Build the Root Cause Agent image"
	@echo "  unified-backend  : Build the Unified Backend image"
	@echo "  ui              : Build the UI image"
	@echo ""
	@echo "Environment variables:"
	@echo "  CONTAINER_CMD : Container command to use (default: podman if available, otherwise docker)"
	@echo "  REGISTRY     : Container registry to push images to (default: localhost:5000)"
	@echo "  TAG          : Image tag to use (default: latest)"
	@echo "  NAMESPACE    : Kubernetes namespace to deploy to (default: observability)"
	@echo "  RELEASE_NAME : Helm release name (default: observability-agent)"
	@echo "  PROMETHEUS_URL : URL for Prometheus (default: http://prometheus-server.monitoring:9090)"
	@echo "  LOKI_URL     : URL for Loki (default: http://loki-gateway.monitoring:3100)"

# Build all container images
build: $(COMPONENTS)

# Push all container images to registry
push:
	@for component in $(COMPONENTS); do \
		echo "Pushing $(REGISTRY)/observability-agent-$$component:$(TAG)"; \
		$(CONTAINER_CMD) push $(REGISTRY)/observability-agent-$$component:$(TAG); \
	done

# Deploy the Helm chart
deploy:
	helm upgrade --install $(RELEASE_NAME) ./helm/observability-agent \
		--namespace $(NAMESPACE) --create-namespace \
		--set global.imageRegistry=$(REGISTRY)/ \
		--set observabilityAgent.prometheus.url=$(PROMETHEUS_URL) \
		--set observabilityAgent.loki.url=$(LOKI_URL) \
		--set orchestrator.image.tag=$(TAG) \
		--set observabilityAgent.image.tag=$(TAG) \
		--set infrastructureAgent.image.tag=$(TAG) \
		--set communicationAgent.image.tag=$(TAG) \
		--set rootCauseAgent.image.tag=$(TAG) \
		--set unifiedBackend.image.tag=$(TAG) \
		--set ui.image.tag=$(TAG)

# Remove all container images
clean:
	@for component in $(COMPONENTS); do \
		echo "Removing $(REGISTRY)/observability-agent-$$component:$(TAG)"; \
		$(CONTAINER_CMD) rmi $(REGISTRY)/observability-agent-$$component:$(TAG) || true; \
	done

# Individual component targets
orchestrator:
	$(CONTAINER_CMD) build --platform=$(PLATFORM) -t $(REGISTRY)/observability-agent-orchestrator:$(TAG) -f orchestrator/Dockerfile .

observability-agent:
	$(CONTAINER_CMD) build --platform=$(PLATFORM) -t $(REGISTRY)/observability-agent-observability-agent:$(TAG) -f agents/observability_agent/Dockerfile .

infrastructure-agent:
	$(CONTAINER_CMD) build --platform=$(PLATFORM) -t $(REGISTRY)/observability-agent-infrastructure-agent:$(TAG) -f agents/infrastructure_agent/Dockerfile .

communication-agent:
	$(CONTAINER_CMD) build --platform=$(PLATFORM) -t $(REGISTRY)/observability-agent-communication-agent:$(TAG) -f agents/communication_agent/Dockerfile .

root-cause-agent:
	$(CONTAINER_CMD) build --platform=$(PLATFORM) -t $(REGISTRY)/observability-agent-root-cause-agent:$(TAG) -f agents/root_cause_agent/Dockerfile .

unified-backend:
	$(CONTAINER_CMD) build --platform=$(PLATFORM) -t $(REGISTRY)/observability-agent-unified-backend:$(TAG) -f ui/unified-backend/Dockerfile ui/unified-backend

ui:
	@echo "Building UI React app locally first..."
	cd ui && npm run build
	@echo "Building UI container with pre-built assets..."
	$(CONTAINER_CMD) build --platform=$(PLATFORM) -t $(REGISTRY)/observability-agent-ui:$(TAG) -f ui/Dockerfile.prebuild ui


# Tool targets
alert-publisher:
	$(CONTAINER_CMD) build --platform=$(PLATFORM) -t $(REGISTRY)/alert-publisher:$(TAG) -f scripts/Dockerfile.alert-publisher scripts/

run:
	$(COMPOSE_CMD) up --build
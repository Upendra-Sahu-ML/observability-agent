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
COMPONENTS = orchestrator metric-agent log-agent deployment-agent root-cause-agent runbook-agent tracing-agent notification-agent postmortem-agent

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
	@echo "  metric-agent     : Build the Metric Agent image"
	@echo "  log-agent        : Build the Log Agent image"
	@echo "  deployment-agent : Build the Deployment Agent image"
	@echo "  root-cause-agent : Build the Root Cause Agent image"
	@echo "  runbook-agent    : Build the Runbook Agent image"
	@echo "  tracing-agent    : Build the Tracing Agent image"
	@echo "  notification-agent : Build the Notification Agent image"
	@echo "  postmortem-agent : Build the Postmortem Agent image"
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
		--set metricAgent.prometheus.url=$(PROMETHEUS_URL) \
		--set logAgent.loki.url=$(LOKI_URL) \
		--set orchestrator.image.tag=$(TAG) \
		--set metricAgent.image.tag=$(TAG) \
		--set logAgent.image.tag=$(TAG) \
		--set deploymentAgent.image.tag=$(TAG) \
		--set rootCauseAgent.image.tag=$(TAG) \
		--set runbookAgent.image.tag=$(TAG) \
		--set tracingAgent.image.tag=$(TAG) \
		--set notificationAgent.image.tag=$(TAG) \
		--set postmortemAgent.image.tag=$(TAG)

# Remove all container images
clean:
	@for component in $(COMPONENTS); do \
		echo "Removing $(REGISTRY)/observability-agent-$$component:$(TAG)"; \
		$(CONTAINER_CMD) rmi $(REGISTRY)/observability-agent-$$component:$(TAG) || true; \
	done

# Individual component targets
orchestrator:
	$(CONTAINER_CMD) build --platform=$(PLATFORM) -t $(REGISTRY)/observability-agent-orchestrator:$(TAG) -f orchestrator/Dockerfile .

metric-agent:
	$(CONTAINER_CMD) build --platform=$(PLATFORM) -t $(REGISTRY)/observability-agent-metric-agent:$(TAG) -f agents/metric_agent/Dockerfile .

log-agent:
	$(CONTAINER_CMD) build --platform=$(PLATFORM) -t $(REGISTRY)/observability-agent-log-agent:$(TAG) -f agents/log_agent/Dockerfile .

deployment-agent:
	$(CONTAINER_CMD) build --platform=$(PLATFORM) -t $(REGISTRY)/observability-agent-deployment-agent:$(TAG) -f agents/deployment_agent/Dockerfile .

root-cause-agent:
	$(CONTAINER_CMD) build --platform=$(PLATFORM) -t $(REGISTRY)/observability-agent-root-cause-agent:$(TAG) -f agents/root_cause_agent/Dockerfile .

runbook-agent:
	$(CONTAINER_CMD) build --platform=$(PLATFORM) -t $(REGISTRY)/observability-agent-runbook-agent:$(TAG) -f agents/runbook_agent/Dockerfile .

tracing-agent:
	$(CONTAINER_CMD) build --platform=$(PLATFORM) -t $(REGISTRY)/observability-agent-tracing-agent:$(TAG) -f agents/tracing_agent/Dockerfile .

notification-agent:
	$(CONTAINER_CMD) build --platform=$(PLATFORM) -t $(REGISTRY)/observability-agent-notification-agent:$(TAG) -f agents/notification_agent/Dockerfile .

postmortem-agent:
	$(CONTAINER_CMD) build --platform=$(PLATFORM) -t $(REGISTRY)/observability-agent-postmortem-agent:$(TAG) -f agents/postmortem_agent/Dockerfile .

# Tool targets
alert-publisher:
	$(CONTAINER_CMD) build --platform=$(PLATFORM) -t $(REGISTRY)/alert-publisher:$(TAG) -f scripts/Dockerfile.alert-publisher scripts/

run:
	$(COMPOSE_CMD) up --build
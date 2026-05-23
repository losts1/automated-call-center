# Makefile for Automated Call Center

.PHONY: setup test docker-up docker-down help

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Install dependencies and set up environment
	pip install -r requirements.txt
	@echo "Setup complete. Configure .env with your credentials."

docker-up: ## Start LiveKit and Redis via Docker Compose
	sudo docker compose up -d

docker-down: ## Stop LiveKit and Redis
	sudo docker compose down --remove-orphans

docker-restart: ## Restart LiveKit
	sudo docker compose restart livekit

test: ## Run AWS mock tests
	python3 agent/aws_mock.py

webhook: ## Start webhook server locally
	python3 webhooks/twilio.py

twilio-config: ## Configure Twilio phone number
	python3 scripts/configure_twilio.py

sip-setup: ## Run full Twilio SIP setup (webhook + tunnel + config)
	bash scripts/setup_twilio.sh

clean: ## Remove cached files
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf *.egg-info/ dist/ build/ .venv/

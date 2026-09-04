SHELL := /bin/bash
COMPOSE := docker compose
DEV := docker compose -f docker-compose.yml -f docker-compose.dev.yml

.PHONY: help init up down dev logs ps seed migrate revision test-radius test-backend restore-drill build fmt clean tls

help: ## Lista os alvos disponíveis
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n",$$1,$$2}'

init: ## Cria .env a partir do exemplo e gera segredos (só precisa de openssl)
	@if [ -f .env ]; then echo ">> .env já existe, nada a fazer."; exit 0; fi
	@cp .env.example .env
	@JWT=$$(openssl rand -hex 32); \
	 FERNET=$$(openssl rand -base64 32 | tr '+/' '-_'); \
	 BACKUP_KEY=$$(openssl rand -base64 32); \
	 RP=$$(openssl rand -hex 12); BP=$$(openssl rand -hex 12); RA=$$(openssl rand -hex 12); \
	 RD=$$(openssl rand -hex 12); AP=$$(openssl rand -base64 12); \
	 sed -i \
	   -e "s|^JWT_SECRET=.*|JWT_SECRET=$$JWT|" \
	   -e "s|^FERNET_KEY=.*|FERNET_KEY=$$FERNET|" \
	   -e "s|^BACKUP_ENCRYPTION_KEY=.*|BACKUP_ENCRYPTION_KEY=$$BACKUP_KEY|" \
	   -e "s|^MYSQL_ROOT_PASSWORD=.*|MYSQL_ROOT_PASSWORD=$$RP|" \
	   -e "s|^MYSQL_BACKEND_PASSWORD=.*|MYSQL_BACKEND_PASSWORD=$$BP|" \
	   -e "s|^MYSQL_RADIUS_PASSWORD=.*|MYSQL_RADIUS_PASSWORD=$$RA|" \
	   -e "s|^REDIS_PASSWORD=.*|REDIS_PASSWORD=$$RD|" \
	   -e "s|^BOOTSTRAP_ADMIN_PASSWORD=.*|BOOTSTRAP_ADMIN_PASSWORD=$$AP|" \
	   .env
	@echo ">> .env criado com segredos aleatórios."
	@echo ">> Senha do admin do painel: $$(grep ^BOOTSTRAP_ADMIN_PASSWORD= .env | cut -d= -f2-)"

secrets: ## Gera ./secrets/{jwt_secret,fernet_key} p/ o overlay docker-compose.secrets.yml
	@mkdir -p secrets
	@test -s secrets/jwt_secret || openssl rand -hex 32 > secrets/jwt_secret
	@test -s secrets/fernet_key || openssl rand -base64 32 | tr '+/' '-_' > secrets/fernet_key
	@chmod 600 secrets/jwt_secret secrets/fernet_key
	@echo ">> secrets/jwt_secret e secrets/fernet_key prontos. Suba com:"
	@echo "   docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d"

tls: ## Gera certificado self-signed para o proxy (dev)
	@mkdir -p proxy/tls
	@openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
		-keyout proxy/tls/server.key -out proxy/tls/server.crt \
		-subj "/CN=$${PUBLIC_HOST:-localhost}" \
		-addext "subjectAltName=DNS:$${PUBLIC_HOST:-localhost},DNS:localhost,IP:127.0.0.1"
	@echo ">> proxy/tls/server.{crt,key} gerados."

build: ## Builda todas as imagens
	$(COMPOSE) build

up: ## Sobe a stack (atrás de reverse proxy externo) — painel em http://localhost:8080
	$(COMPOSE) up -d

up-tls: ## Sobe a stack com o proxy TLS embutido — painel em https://localhost
	$(COMPOSE) --profile tls-proxy up -d

dev: ## Teste local HTTP (COOKIE_SECURE=false, reload, +adminer) — http://localhost:8080
	$(DEV) --profile dev up -d

down: ## Derruba a stack (mantém volumes)
	$(COMPOSE) down

clean: ## Derruba a stack e APAGA os volumes (destrói o banco)
	$(COMPOSE) down -v

ps: ## Status dos containers
	$(COMPOSE) ps

logs: ## Segue os logs de todos os serviços
	$(COMPOSE) logs -f --tail=100

migrate: ## Aplica as migrações Alembic
	$(COMPOSE) exec backend alembic upgrade head

revision: ## Cria nova migração autogerada: make revision m="mensagem"
	$(COMPOSE) exec backend alembic revision --autogenerate -m "$(m)"

seed: ## Popula fabricantes, perfis e primeiro admin
	$(COMPOSE) exec backend python -m app.seed

test-backend: ## Roda a suíte pytest do backend (imagem própria, sem tocar na stack)
	docker build --build-arg INSTALL_DEV=true -t pulse-radius-backend-test ./backend
	docker run --rm \
	  -e JWT_SECRET=test-secret-0000000000000000000000000000000000 \
	  -e FERNET_KEY=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= \
	  -e DATABASE_URL=sqlite+pysqlite:///:memory: \
	  pulse-radius-backend-test sh -c 'ruff check app tests && pytest -q'

restore-drill: ## Testa de verdade a restauração do último backup (MySQL efêmero e descartável)
	./scripts/restore_drill.sh

test-radius: ## radtest de sanidade contra o FreeRADIUS
	$(COMPOSE) exec freeradius radtest $(u) $(p) 127.0.0.1 0 $${RADIUS_TEST_SECRET:-testing123}

fmt: ## Formata backend (ruff) e frontend (prettier)
	$(COMPOSE) exec backend ruff format app tests && $(COMPOSE) exec backend ruff check --fix app tests

# Pulse RADIUS

Sistema AAA completo para **login administrativo em equipamentos de rede** via RADIUS,
com painel web para gestão. Stack: **FreeRADIUS 3.2 + MySQL 8** para o AAA,
**FastAPI** no backend, **React + Vite** no frontend, tudo em **Docker**.

| Camada | O que faz |
|---|---|
| **Authentication** | Valida usuário/senha (PAP, senha em hash SSHA2-512 no `radcheck`). |
| **Authorization** | Perfil de privilégio → atributos RADIUS por fabricante (Huawei, Juniper, Datacom, Mikrotik, A10). |
| **Accounting** | Start/Interim/Stop em `radacct`; tentativas de auth em `radpostauth`; dashboard e export CSV. |

O painel permite cadastrar: **usuários de autenticação**, **equipamentos** (agrupados por
fabricante), **perfis de privilégio** e **usuários do próprio painel**. Toda ação
administrativa é gravada em log de auditoria.

## Arquitetura

```
   navegador ──HTTPS──▶ reverse proxy ──HTTP──▶ ┌──────────┐ /api  ┌─────────┐
                        (NPM / Caddy / LB          │ frontend │──────▶│ backend │──┐
                         ou proxy embutido)        │  (nginx) │       └─────────┘  │ SQLAlchemy
                                                   └──────────┘                    ▼
   equipamentos ──RADIUS 1812/1813 udp──▶ ┌────────────┐              ┌──────────┐
   (NAS)                                  │ freeradius │─────────────▶│  MySQL   │
                                          └────────────┘              └──────────┘
```

O container `frontend` serve a SPA e encaminha `/api` para o `backend` — é o
entrypoint HTTP. TLS/domínio ficam a cargo de um reverse proxy (externo, ex.
Nginx Proxy Manager, ou o proxy embutido no profile `tls-proxy`).

O backend escreve nas tabelas `app_*` **e** nas tabelas do FreeRADIUS (`radcheck`,
`radusergroup`, `radgroupreply`, `nas`) na mesma transação — cadastrar um usuário no
painel o torna autenticável imediatamente; cadastrar um equipamento o torna um cliente
RADIUS válido (resolução dinâmica via SQL, sem reload).

## Quickstart

Pré-requisitos: Docker + Docker Compose. `openssl` (para gerar os segredos) e,
opcionalmente, `make` — sem `make`, use o bloco de "Teste local" abaixo.

```bash
make init      # cria .env com JWT_SECRET e FERNET_KEY gerados — revise as senhas!
make build
make up        # sobe db, freeradius, backend, frontend
```

O backend aplica as migrações e roda o seed automaticamente no start
(4 fabricantes, perfis `admin-full` / `operator` / `read-only`, e o primeiro
`superadmin` a partir de `BOOTSTRAP_ADMIN_*`).

O painel (SPA + `/api`) fica em **http://\<servidor\>:${WEB_PORT:-8080}**.
RADIUS: `<servidor>:1812/udp` (auth) e `:1813/udp` (accounting).

### Publicar com TLS

- **Reverse proxy externo (recomendado)** — Nginx Proxy Manager, Caddy, LB da
  nuvem etc. Aponte-o para `http://<IP-privado-do-servidor>:${WEB_PORT}`. Ajuste
  `FRONTEND_ORIGIN` (URL pública) e `FORWARDED_ALLOW_IPS` (IP do proxy).
  Passo a passo: [docs/deploy-behind-npm.md](docs/deploy-behind-npm.md).
- **Proxy TLS embutido** (sem proxy externo): `make tls` e
  `docker compose --profile tls-proxy up -d` → **https://\<PUBLIC_HOST\>**.

### Teste local (sem proxy)

Como o modo padrão assume um proxy HTTPS na frente, para rodar em `http://localhost`
use o override de dev (`COOKIE_SECURE=false`, migração+seed e reload automáticos).

**Sem `make`** — crie o `.env` com uma linha (só precisa de `openssl`):

```bash
cp .env.example .env
sed -i \
  -e "s|^JWT_SECRET=.*|JWT_SECRET=$(openssl rand -hex 32)|" \
  -e "s|^FERNET_KEY=.*|FERNET_KEY=$(openssl rand -base64 32 | tr '+/' '-_')|" \
  -e "s|^MYSQL_ROOT_PASSWORD=.*|MYSQL_ROOT_PASSWORD=pulse_root|" \
  -e "s|^MYSQL_BACKEND_PASSWORD=.*|MYSQL_BACKEND_PASSWORD=pulse_backend|" \
  -e "s|^MYSQL_RADIUS_PASSWORD=.*|MYSQL_RADIUS_PASSWORD=pulse_radius|" \
  -e "s|^BOOTSTRAP_ADMIN_PASSWORD=.*|BOOTSTRAP_ADMIN_PASSWORD=Pulse!admin123|" \
  .env

docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
#  painel:  http://localhost:8080      (login: admin / Pulse!admin123)
#  API:     http://localhost:8000/api/docs
#  MySQL:   localhost:3306   ·   RADIUS: localhost:1812-1813/udp
```

(Com `make`: `make init && docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build` —
instale com `sudo apt-get install -y make`.)

Alternativas:

- `make up-tls` — sobe o proxy TLS embutido; abra **https://localhost** (aceite o
  certificado self-signed). Fica igual à produção, com `COOKIE_SECURE=true`.
- **Front com hot-reload**: `make dev` (backend/DB via Docker) e, à parte,
  `cd frontend && npm install && npm run dev` → Vite em **http://localhost:5173**
  (faz proxy de `/api` para `:8000`).

> Não abra `http://localhost:8080` com `COOKIE_SECURE=true` no `.env` — o navegador
> descarta os cookies `Secure` em HTTP e o login fica em loop. O override de dev já
> cuida disso.

## Verificação ponta a ponta

```bash
# 1. cadastre no painel: equipamento Huawei 10.0.0.1 (secret "s3cr3t"),
#    perfil admin-full, usuário noc.jdoe

# 2. teste a autenticação de dentro do container
make test-radius u=noc.jdoe p='SenhaForte!'
#  -> Access-Accept + Huawei-Exec-Privilege = 15

# 3. accounting
docker compose exec freeradius radclient -x 127.0.0.1:1813 acct testing123 <<'EOF'
User-Name = "noc.jdoe"
Acct-Status-Type = Start
Acct-Session-Id = "sess-001"
NAS-IP-Address = 10.0.0.1
EOF
#  -> linha em radacct, visível na página Accounting

# 4. suíte de testes do backend
make test-backend
```

## Estrutura

```
backend/     FastAPI + SQLAlchemy + Alembic  (app/api, app/models, app/services)
frontend/    React + Vite + TS + Tailwind    (src/features/*)
radius/      Dockerfile + overrides do FreeRADIUS 3.2
db/init/     schema oficial do FreeRADIUS + criação dos usuários de serviço
proxy/       nginx (TLS, roteamento /api e SPA)
docs/        ARCHITECTURE, RUNBOOK e snippets de configuração por fabricante
```

Ver [ARCHITECTURE](docs/ARCHITECTURE.md), [RUNBOOK](docs/RUNBOOK.md), [SECURITY](docs/SECURITY.md) e [deploy atrás do NPM](docs/deploy-behind-npm.md).

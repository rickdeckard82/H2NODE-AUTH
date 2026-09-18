# Pulse RADIUS

Sistema AAA completo para **login administrativo em equipamentos de rede** via
**RADIUS e TACACS+**, com painel web para gerenciamento. Stack: **FreeRADIUS 3.2 +
tac_plus-ng + MySQL 8** para o AAA, **FastAPI** no backend, **React + Vite** no
frontend, tudo em **Docker**.

| Camada | O que faz |
|---|---|
| **Authentication** | Valida usuário/senha. RADIUS: PAP + MS-CHAPv2 (hash SSHA2-512 / NT no `radcheck`). TACACS+: resolvido em tempo de request pelo MAVIS contra o mesmo MySQL. |
| **Authorization** | Perfil de privilégio → atributos RADIUS por fabricante (Huawei, Juniper, Datacom, Mikrotik, A10) ou `priv-lvl` + AV pairs no TACACS+. Allowlist de IP de origem por grupo de usuário. |
| **Accounting** | Start/Interim/Stop em `radacct`; tentativas de auth em `radpostauth`; comandos executados em `cmd_acct`; dashboard de 7 dias e export CSV. |

O painel permite cadastrar **usuários de autenticação**, **equipamentos**
(agrupados por fabricante, cada um falando RADIUS **ou** TACACS+), **grupos de
usuário** (restrição por IP), **perfis de privilégio** e os **usuários do próprio
painel**. Toda ação administrativa vai para um log de auditoria.

## Recursos

- **RADIUS + TACACS+** lado a lado, mesmos usuários/perfis/grupos; protocolo
  escolhido por equipamento (ou herdado do grupo). Segredo RADIUS e chave TACACS+
  herdáveis do grupo, cifrados em repouso (Fernet).
- **Papéis (RBAC)**: `superadmin` / `admin` / `operator` / `auditor`, com o menu e
  as rotas filtrados por papel.
- **2FA (TOTP)** para o painel: QR code, códigos de recuperação de uso único e
  "lembrar deste dispositivo" (pula o código por 30 dias, com gerenciamento e
  auditoria).
- **Segurança**: login JWT + refresh com rotação e detecção de reuso, bloqueio de
  login progressivo, CSRF (double-submit), cabeçalhos de segurança, rate-limit,
  backups cifrados.
- **Convite por e-mail (SMTP)** para o novo usuário do painel criar a própria senha.
- **LGPD**: identificação do controlador no Aviso de Privacidade e prazos de
  retenção configuráveis (logins/accounting, auditoria, usuários inativos) com
  **exclusão automática** diária.
- **Idioma** pt-BR / en-US, definido no cadastro do usuário e trocável no menu.
- **Relatórios** Authentication / Authorization / Accounting + Auditoria, com
  filtros, IP de origem/destino e export CSV.

## Arquitetura

```
   navegador ──HTTPS──▶ reverse proxy ──HTTP──▶ ┌──────────┐ /api  ┌─────────┐
                        (NPM / Caddy / LB          │ frontend │──────▶│ backend │──┐
                         ou proxy embutido)        │  (nginx) │       └─────────┘  │ SQLAlchemy
                                                   └──────────┘                    ▼
   equipamentos ──RADIUS 1812/1813 udp──▶ ┌────────────┐              ┌──────────┐
   (NAS)        ──TACACS+ 49/tcp──────────▶│ freeradius │─────────────▶│  MySQL   │
                                          │  + tacacs  │◀────────────▶└──────────┘
                                          └────────────┘   MAVIS
```

O container `frontend` serve a SPA e encaminha `/api` para o `backend` — é o
entrypoint HTTP. TLS/domínio ficam a cargo de um reverse proxy (externo, ex.
Nginx Proxy Manager, ou o proxy embutido no profile `tls-proxy`).

O backend escreve nas tabelas `app_*` **e** nas tabelas do FreeRADIUS (`radcheck`,
`radusergroup`, `radgroupreply`, `nas`) na mesma transação — cadastrar um usuário
no painel o torna autenticável imediatamente. O serviço `tacacs` (tac_plus-ng)
recarrega os clientes/perfis a partir de um arquivo gerado pelo painel e resolve
usuário/senha/grupo em tempo de request pelo MAVIS, contra o mesmo MySQL.

## Quickstart

Pré-requisitos: Docker + Docker Compose. `openssl` (para gerar os segredos) e,
opcionalmente, `make` — sem `make`, use o bloco de "Teste local" abaixo.

```bash
make init      # cria .env com JWT_SECRET e FERNET_KEY gerados — revise as senhas!
make build
make up        # sobe db, freeradius, tacacs, backend, frontend
```

O backend aplica as migrações e roda o seed automaticamente no start
(6 fabricantes, perfis `admin-full` / `operator` / `read-only`, uma linha de
configuração LGPD com retenções zeradas, e o primeiro `superadmin` a partir de
`BOOTSTRAP_ADMIN_*`).

> **Atualizando uma instalação existente**: as migrações rodam no start do
> container; para aplicá-las sem recriar tudo, `make migrate`.

O painel (SPA + `/api`) fica em **http://\<servidor\>:${WEB_PORT:-8080}**.
RADIUS: `<servidor>:1812/udp` (auth) e `:1813/udp` (accounting). TACACS+: `:49/tcp`.

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
#  MySQL:   localhost:3306   ·   RADIUS: localhost:1812-1813/udp   ·   TACACS+: localhost:49/tcp
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
frontend/    React + Vite + TS + Tailwind    (src/features/*, src/lib/i18n)
radius/      Dockerfile + overrides do FreeRADIUS 3.2
tacacs/      tac_plus-ng + MAVIS (pulse_mavis.py) + importadores de accounting
db/init/     schema oficial do FreeRADIUS + criação dos usuários de serviço
proxy/       nginx (TLS, roteamento /api e SPA)
docs/        ARCHITECTURE, RUNBOOK, SECURITY e snippets de configuração por fabricante
```

Ver [ARCHITECTURE](docs/ARCHITECTURE.md), [RUNBOOK](docs/RUNBOOK.md), [SECURITY](docs/SECURITY.md) e [deploy atrás do NPM](docs/deploy-behind-npm.md).

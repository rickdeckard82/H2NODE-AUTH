# Arquitetura — Pulse RADIUS

## Componentes

| Container | Imagem | Rede | Portas |
|---|---|---|---|
| `db` | mysql:8.4 | internal | 3306 (só `--profile dev`) |
| `freeradius` | build (freeradius:3.2) | internal | 1812/udp, 1813/udp |
| `backend` | build (python:3.12) | edge + internal | 8000 (interno) |
| `frontend` | build (node → nginx) | edge | 80 (interno) |
| `proxy` | build (nginx) | edge | 80, 443 |
| `adminer` | adminer:4 | internal + edge | 8080 (só `--profile dev`) |

`internal` é uma rede Docker sem acesso à internet. O `db` nunca é exposto ao host
em produção.

## Banco de dados (`radius`)

### Tabelas do FreeRADIUS (schema oficial, `db/init/00_radius_schema.sql`)
`radcheck`, `radreply`, `radgroupcheck`, `radgroupreply`, `radusergroup`,
`radacct`, `radpostauth`, `nas`, `nasreload`.

### Tabelas da aplicação (Alembic, prefixo `app_`)
- **`app_system_user`** — contas do painel. Papéis: `superadmin > admin > operator > auditor`.
  Senha em **Argon2id**.
- **`app_manufacturer`** — cadastro de fabricantes (CRUD na página "Fabricantes").
  Campos: `name` (slug), `display_name`, `vendor_kind` (`huawei|juniper|datacom|
  mikrotik|generic` — controla a tradução de VSA), `radius_vendor_id`,
  `radius_secret_enc` (**segredo RADIUS padrão**, Fernet), `notes`. O seed cria os
  4 comuns como ponto de partida (editáveis/removíveis, sem segredo).
- **`app_privilege_profile`** + **`app_privilege_profile_attr`** — perfil abstrato e o
  mapeamento *(fabricante, atributo, op, valor)*. Fonte de verdade que gera as linhas
  de `radgroupreply` do grupo `profile_<nome>`.
- **`app_equipment`** — NAS/cliente RADIUS. `radius_secret` cifrado com **Fernet**.
  Espelhado na tabela `nas` (chave: `mgmt_ip` → `nasname`).
- **`app_auth_user`** — metadados do usuário que autentica nos equipamentos. Espelhado
  em `radcheck` (senha SSHA2-512) + `radusergroup` (grupo do perfil). Pode pertencer
  a um **grupo de usuário** (`auth_group_id`).
- **`app_auth_user_group`** + **`app_auth_group_cidr`** — grupo com *allowlist* de IP
  de origem. `app_auth_group_cidr` guarda os limites em binário compatível com
  `INET6_ATON()`. No `authorize`, se o usuário tem grupo e nenhuma faixa cobre o
  `Packet-Src-IP-Address`, o FreeRADIUS rejeita.
- **`app_audit_log`** — toda ação administrativa (autor, IP, diff antes/depois).
- **`app_refresh_token`** — rotação/revogação de refresh tokens.

### Usuários MySQL (privilégio mínimo, `db/init/01_db_users.sh`)
- `backend_svc` — CRUD completo (app + rad*).
- `radius_svc` — `SELECT` em tudo; `INSERT/UPDATE/DELETE` só em `radacct`, `radpostauth`, `nasreload`.

## Fluxo AAA

### Authentication (Access-Request, PAP)
1. `authorize`: `sql` carrega `radcheck`/`radgroupcheck`/`radgroupreply` do usuário e do grupo.
2. Enforce de estado: consulta `app_auth_user` — se `is_active = 0` ou `expires_at` vencido → **reject**.
3. `pap` valida a senha contra `SSHA2-512-Password`.
4. `radpostauth` registra a tentativa (aceita ou negada).

### Authorization (Access-Accept)
- O grupo `profile_<perfil>` traz em `radgroupreply` **um conjunto de VSAs por fabricante**.
- `post-auth` roda a policy **`vendor-authz`**: descobre o fabricante do NAS de origem
  (join `app_equipment`/`app_manufacturer` pelo `NAS-IP-Address`) e **remove da resposta os
  VSAs dos outros fabricantes**, deixando só o relevante.

### Accounting
- `accounting`: `sql` grava Start / Interim-Update / Stop em `radacct`.
- O painel lê `radacct` (sessões, ativas, agregados, CSV) e `radpostauth` (eventos de auth).

## Clientes RADIUS sem reload

- No boot, `read_clients = yes` carrega todos os `nas` como clientes estáticos.
- Um NAS cadastrado **depois** do boot cai no template `client dynamic` (`0.0.0.0/0`)
  e é resolvido pelo virtual server **`dynamic_clients`**, que consulta a tabela `nas`
  em tempo de request e materializa o cliente (segredo, shortname, tipo). Sem restart.
- Fallback garantido: `docker compose restart freeradius`.

## Segurança

- **Painel**: JWT access (15 min) + refresh (7 d, com rotação e detecção de reuso) em
  cookies `HttpOnly` `Secure` `SameSite=Strict`. CSRF por *double-submit* (`X-CSRF-Token`).
  RBAC por dependência. Rate-limit no `/auth/login`. Headers de segurança em todas as
  respostas e no proxy (HSTS, `X-Frame-Options`, CSP).
- **Segredos em repouso**: `radius_secret` e `mfa_secret` cifrados com Fernet (`FERNET_KEY`).
- **Senhas**: Argon2id (painel), SSHA2-512 (usuários RADIUS — nunca em texto claro).
- **TLS**: terminação no proxy. Dev usa self-signed; produção monta `server.crt`/`server.key`.

## Observabilidade

- `GET /api/health` (liveness + ping no banco).
- `GET /api/metrics` (Prometheus, via `prometheus-fastapi-instrumentator`).
- Logs estruturados (JSON, `structlog`) com `request_id`.

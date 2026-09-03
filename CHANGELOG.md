# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).
A fonte exibida no painel (menu lateral → clicar na versão) é
`frontend/src/lib/changelog.ts` — mantenha os dois em sincronia.

## [0.1.0] — 2026-09-02

Lançamento inicial.

### Adicionado

- **AAA** completo com FreeRADIUS 3.2 + MySQL 8, backend (FastAPI) e frontend
  (React + Vite) separados em Docker.
- **Authentication**: PAP com senha em hash SSHA2-512 (`radcheck`).
- **Authorization**: perfis de privilégio traduzidos para os atributos RADIUS de
  cada fabricante (Huawei, Juniper, Datacom, Mikrotik); a policy `vendor-authz`
  remove da resposta os VSAs dos demais fabricantes.
- **Accounting**: `radacct` (start/interim/stop) e `radpostauth`; dashboard,
  sessões ativas, filtros e exportação CSV.
- Cadastro de **usuários de autenticação**, **equipamentos** (clientes RADIUS) e
  **grupos de equipamentos / fabricantes** com **segredo RADIUS padrão herdável**
  (trocar o segredo do grupo re-propaga aos equipamentos que o herdam).
- Clientes RADIUS resolvidos por SQL em tempo de request (sem reload).
- Painel seguro: JWT access + refresh com rotação e detecção de reuso, RBAC,
  CSRF (double-submit), cabeçalhos de segurança, rate-limit no login.
- **Utilizadores do sistema** (papéis superadmin/admin/operator/auditor) e log de
  auditoria de todas as ações administrativas.
- Tema claro/escuro automático; menu lateral agrupado com ícones e notas de versão.
- Aviso de Privacidade (LGPD) em `/privacidade`, linkado no rodapé — textos
  configuráveis em `frontend/src/lib/legal.ts` (`orgName`, `dpoEmail`, retenções).
- Endurecimento de segurança (ver `docs/SECURITY.md`): bloqueio de conta após 5
  logins malsucedidos, verificação de senha em tempo constante, CSP/Permissions-
  Policy no HTML, `/api/docs` e `/api/metrics` fechados por padrão, `JWT_SECRET`
  mínimo de 32 caracteres validado no boot, senha mínima 12 para credenciais de
  equipamento, `npm ci` no build, `react-router`/FastAPI/cryptography atualizados
  (0 vulnerabilidades no `npm audit`).
- Rate-limit de login compartilhado via **Redis** (`REDIS_URL`); poda automática
  de refresh tokens expirados.
- `radius_svc` com privilégio mínimo (migração `0004`): `SELECT` só nas tabelas
  que o FreeRADIUS lê — sem acesso a `app_system_user` / `app_refresh_token` /
  `app_audit_log`.
- Imagem do backend enxuta em produção (`INSTALL_DEV=false`); overlay
  `docker-compose.secrets.yml` para `JWT_SECRET`/`FERNET_KEY` via arquivo.
- `RADIUS_BIND` / `RADIUS_REQUIRE_MA` configuráveis.
- **Grupos de usuário** (migração `0005`): allowlist de IP de origem (IPv4/IPv6,
  CIDR ou IP simples). Se o usuário está num grupo e o IP de origem do pacote
  RADIUS não casa com nenhuma faixa, o FreeRADIUS rejeita.

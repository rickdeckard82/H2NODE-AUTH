# Postura de segurança — Pulse RADIUS

Resumo do que já está implementado e do que **depende de configuração/infra sua**.

## Já implementado

- **Senhas**: painel em Argon2id; usuários RADIUS em SSHA2-512 (nunca em texto claro).
  Mínimo de 12 caracteres para credenciais de equipamento.
- **Sessão**: JWT access (15 min) + refresh (7 d) com **rotação e detecção de reuso**
  (um refresh token reutilizado revoga toda a árvore de sessões do usuário).
  Cookies `HttpOnly` `Secure` `SameSite=Strict`.
- **Login**: rate-limit por IP (10/min) **+ bloqueio da conta por 15 min após 5
  tentativas malsucedidas**; verificação de senha em tempo constante (hash
  descartável) para não vazar a existência de contas por timing.
- **CSRF**: double-submit (`X-CSRF-Token`) em todas as rotas de escrita, além de
  `SameSite=Strict`.
- **RBAC**: `superadmin > admin > operator > auditor`, checado contra o banco a
  cada request (mudança de papel/desativação tem efeito imediato).
- **Injeção**: backend usa exclusivamente SQLAlchemy com bind params (sem SQL
  cru). No FreeRADIUS, os `%{sql:...}` inline são protegidos por allowlist estrita
  de `User-Name` (`^[A-Za-z0-9._@-]+$`).
- **Segredos em repouso**: `radius_secret` de equipamentos e fabricantes cifrados
  com Fernet. `JWT_SECRET` exige ≥ 32 caracteres (validado no boot).
- **Cabeçalhos**: CSP, `X-Frame-Options: DENY`, `X-Content-Type-Options`,
  `Referrer-Policy`, `Permissions-Policy` no HTML; HSTS no proxy TLS.
- **Superfície**: `/api/docs` e `/api/openapi.json` desligados por padrão
  (`ENABLE_DOCS=false`); `/api/metrics` bloqueado na borda (só rede interna).
- **Rede**: `db` e `freeradius` na rede Docker `internal` (sem internet); `backend`
  sem porta publicada (só acessível via `frontend`).
- **Containers**: backend roda como usuário não-root; imagem do frontend com
  `npm ci` (build reprodutível a partir do lockfile).
- **Dependências**: `npm audit` = 0 vulnerabilidades; `react-router` 7, FastAPI
  0.118 (Starlette com patch de upload), `cryptography` 44.0.1.
- **Rate-limit compartilhado**: com `REDIS_URL` (padrão no compose), o limite de
  login é único entre todos os workers e sobrevive a reinícios.
- **Poda de tokens**: refresh tokens expirados/revogados são limpos no login.
- **`radius_svc` sem acesso a dados sensíveis**: `SELECT` só nas tabelas que o
  FreeRADIUS lê (`rad*`, `nas`, `app_auth_user`, `app_equipment`,
  `app_manufacturer`) — **não** lê `app_system_user`, `app_refresh_token` nem
  `app_audit_log`.
- **Imagem do backend enxuta em produção** (`INSTALL_DEV=false` por padrão; deps
  de teste só no modo dev).
- **Segredos como arquivo** (opcional): overlay `docker-compose.secrets.yml` +
  `make secrets` leem `JWT_SECRET`/`FERNET_KEY` de `/run/secrets/*` — não
  aparecem em `docker inspect`. Deixe as linhas `JWT_SECRET=`/`FERNET_KEY=` do
  `.env` vazias ao usar o overlay.

## Depende de você (infra / configuração)

1. **X-Forwarded-For confiável.** No Nginx Proxy Manager, use
   `proxy_set_header X-Forwarded-For $remote_addr;` (**substituir**, não anexar) e
   defina `FORWARDED_ALLOW_IPS` com o IP do NPM (não `*`). Sem isso, o IP na
   auditoria pode ser forjado pelo cliente.
2. **Firewall.** Exponha `WEB_PORT` só para o servidor do NPM; `1812-1813/udp` só
   para a rede de gerência (`RADIUS_BIND` para fixar a interface). Nada mais.
3. **Segredos.** `.env` com permissão `600`, fora de backup não cifrado. Guarde
   `FERNET_KEY` e `JWT_SECRET` em local seguro (sem `FERNET_KEY` os segredos
   cifrados são irrecuperáveis). Rotacione o primeiro admin após o bootstrap.
4. **Backups do MySQL.** Os dumps contêm hashes de senha e os *shared secrets*
   RADIUS em claro (coluna `nas.secret`) — cifre os backups em repouso.
5. **TLS.** Certificado válido no proxy (Let's Encrypt no NPM); nunca sirva o
   painel em HTTP puro fora de `localhost`.

## Itens que continuam em aberto

- **`RADIUS_REQUIRE_MA`**: `auto` por padrão (exige Message-Authenticator de quem
  já envia). Se todo o parque suporta, mude para `yes` no `.env`.
- **`FORWARDED_ALLOW_IPS`**: `*` por padrão. Pinne no IP do NPM em produção
  (item 1 acima).
- **CoA/Disconnect (3799/udp)**: fora do escopo desta versão; se habilitar,
  restrinja no firewall.
- **Separação de banco**: `app_system_user`/`app_refresh_token`/`app_audit_log`
  ainda vivem no schema `radius` (o `radius_svc` só não tem *grant* neles).
  Mover para um schema dedicado é possível numa versão futura, mas envolve FKs
  entre bancos e complica dump/restore — o grant mínimo já resolve o vetor.

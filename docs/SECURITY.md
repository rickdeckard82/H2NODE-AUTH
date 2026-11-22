# Postura de segurança — H2NODE Auth

Resumo do que já está implementado e do que **depende de configuração/infra sua**.

## Já implementado

- **Senhas**: painel em Argon2id; usuários RADIUS em SSHA2-512 (nunca em texto claro).
  Mínimo de 12 caracteres para credenciais de equipamento.
- **Sessão**: JWT access (15 min) + refresh (7 d) com **rotação e detecção de reuso**
  (um refresh token reutilizado revoga toda a árvore de sessões do usuário).
  Cookies `HttpOnly` `Secure` `SameSite=Strict`.
- **Login**: rate-limit por IP (10/min) **+ bloqueio da conta com backoff
  exponencial** após 5 tentativas malsucedidas (15min, 30min, 60min... até um
  teto de 24h — cresce a cada nova ofensa, zera no primeiro login correto);
  verificação de senha em tempo constante (hash descartável) para não vazar a
  existência de contas por timing. `POST /auth/invite/accept`,
  `POST /auth/mfa/verify` e `PATCH /auth/me/password` também têm rate-limit.
- **2FA (TOTP)**: opcional e self-service para qualquer usuário do painel
  (`POST /auth/mfa/setup|enable|disable`); o painel avisa `admin`/`superadmin`
  sem 2FA ativo. Ao ativar, o sistema gera **10 códigos de recuperação** de uso
  único (exibidos uma só vez; guardados só como hash Argon2). Cada código vale
  como 2ª etapa no login (`POST /auth/mfa/verify`) ou para desativar o 2FA
  (`POST /auth/mfa/disable`) quando o dispositivo TOTP é perdido; um lote novo
  pode ser gerado a qualquer momento (`POST /auth/mfa/recovery-codes/regenerate`,
  invalida os anteriores). Recovery adicional: um `superadmin` pode resetar o 2FA
  de outro usuário (`POST /system-users/{id}/reset-mfa`).
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
- **Rede**: `db` publicado só em `127.0.0.1` do host (alcançado por `freeradius` e
  `tacacs`, que usam a rede do host); `redis` só na rede Docker `internal` (sem
  internet); `backend` sem porta publicada (só acessível via `frontend`).
- **Containers**: backend roda como usuário não-root; imagem do frontend com
  `npm ci` (build reprodutível a partir do lockfile).
- **Dependências**: `npm audit` = 0 vulnerabilidades; `pip-audit` = 0
  vulnerabilidades conhecidas (`cryptography` 50.x, `pyjwt` 2.13, `python-multipart`
  0.0.32, FastAPI 0.141 / Starlette 1.x). Reaudite antes de cada release — versões
  fixadas envelhecem.
- **Backups cifrados**: o `db-backup` automático cifra cada dump com
  `BACKUP_ENCRYPTION_KEY` (AES-256, `openssl enc`) quando ela está definida
  (`make init` já gera). O export manual do painel (`GET /backup/export`) cifra
  com a `FERNET_KEY` do backend por padrão (pode ser desligado na UI).
  `./scripts/restore_drill.sh` (ou `make restore-drill`) prova de verdade que o
  último backup restaura — sobe um MySQL efêmero, aplica o dump e valida com
  queries de sanidade; agende no cron.
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
   defina `FORWARDED_ALLOW_IPS` com o IP do NPM. O container `frontend` só aceita
   X-Forwarded-For desses IPs (`*` = faixas privadas) e repassa ao backend apenas
   o IP resolvido — é ele que vale no rate-limit, no bloqueio de login e na auditoria.
2. **Firewall.** Exponha `WEB_PORT` só para o servidor do NPM; `1812-1813/udp` só
   para a rede de gerência, e `49/tcp` idem (freeradius e tacacs usam `network_mode: host`,
   então o `ufw allow from <rede> to any port …` comum filtra; não precisa de ufw-docker
   para eles). Nada mais.
3. **Segredos.** `.env` com permissão `600`, fora de backup não cifrado. Guarde
   `FERNET_KEY` e `JWT_SECRET` em local seguro (sem `FERNET_KEY` os segredos
   cifrados são irrecuperáveis). Rotacione o primeiro admin após o bootstrap.
4. **Backups do MySQL.** Os dumps contêm hashes de senha e os *shared secrets*
   RADIUS em claro (coluna `nas.secret`). O `db-backup` automático já cifra
   sozinho se `BACKUP_ENCRYPTION_KEY` estiver definida (item resolvido pelo
   repositório) — garanta que ela está no `.env` de produção.
5. **TLS.** Certificado válido no proxy (Let's Encrypt no NPM); nunca sirva o
   painel em HTTP puro fora de `localhost`. Confirme que a borda manda
   `Strict-Transport-Security` — nem o `backend` nem o `frontend` deste stack
   enviam HSTS por conta própria fora do profile `tls-proxy`.
6. **SSH e firewall do host.** `PasswordAuthentication no` + `PermitRootLogin no`
   no `sshd_config`; `ufw`/`nftables` liberando só as portas da tabela em
   `docs/deploy-behind-npm.md`. Isso é do sistema operacional, fora do repo —
   comandos prontos em `docs/host-hardening.md`.
7. **Disco cifrado em repouso.** O MySQL deste stack não faz encryption-at-rest
   (sem keyring plugin/TDE); se precisar disso, cifre o disco do host
   (LUKS/dm-crypt) ou use um disco já cifrado do provedor de nuvem — ver
   `docs/host-hardening.md`.

## Itens que continuam em aberto

- **`RADIUS_REQUIRE_MA`**: `auto` por padrão (exige Message-Authenticator de quem
  já envia). Se todo o parque suporta, mude para `yes` no `.env`.
- **`FORWARDED_ALLOW_IPS`**: `*` por padrão (= faixas privadas). Pinne no IP do
  NPM em produção (item 1 acima).
- **CoA/Disconnect (3799/udp)**: fora do escopo desta versão; se habilitar,
  restrinja no firewall.
- **Separação de banco**: `app_system_user`/`app_refresh_token`/`app_audit_log`
  ainda vivem no schema `radius` (o `radius_svc` só não tem *grant* neles).
  Mover para um schema dedicado é possível numa versão futura, mas envolve FKs
  entre bancos e complica dump/restore — o grant mínimo já resolve o vetor.

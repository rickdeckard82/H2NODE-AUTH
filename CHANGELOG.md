# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).
A fonte exibida no painel (menu lateral → clicar na versão) é
`frontend/src/lib/changelog.ts` — mantenha os dois em sincronia.

## [0.5.0] — 2026-09-09

### Adicionado

- **2FA (TOTP)** para os usuários do painel: QR code no cadastro, **códigos
  de recuperação** de uso único e **“lembrar deste dispositivo”** — grava o
  cookie `pr_td` (SHA-256 no banco, tabela `app_mfa_trusted_device`) e o
  navegador pula a 2ª etapa por 30 dias (janela deslizante,
  `MFA_TRUSTED_DEVICE_TTL_DAYS`). Gestão e revogação no modal de 2FA; os
  dispositivos caem ao desativar o 2FA ou trocar a senha.
- **Bloqueio de login progressivo** (backoff 15 min → 24 h), **revelar segredo
  RADIUS**, **convite de usuário por e-mail** (SMTP configurável),
  **troca da própria senha** e **backups cifrados**.
- **Fabricante A10 Networks ACOS** (Thunder / Thunder CGN) via RADIUS e TACACS+.
- **Exceção por equipamento** à exigência de `Message-Authenticator`
  (`radius_require_message_authenticator`), para NAS com firmware anterior aos
  patches de BlastRADIUS.
- **Chave TACACS+ padrão do grupo**: revelar, status na lista de fabricantes e
  herança visível na lista de equipamentos; o segredo RADIUS é escondido quando
  o grupo fala TACACS+.
- Tela **Authentication** com IP de origem/destino e eventos TACACS+.
- **Painel** repaginado: janela de **7 dias** (antes 24 h), com série diária
  (`/accounting/stats` → `daily[7]`), gráfico de barras empilhadas de
  autenticações por dia e área de sessões por dia; **sucessos e falhas de
  autenticação lado a lado** com IP de origem; botão **Atualizar** nas telas
  Authentication / Authorization / Accounting / Auditoria e no Painel.
- **Auditoria** ganha a aba **“Dispositivos 2FA”**: dispositivos memorizados
  ativos (`GET /audit/trusted-devices`) + histórico de memorização/remoção
  (`entity_type = mfa_trusted_device`).
- **Configuração → LGPD** (`app_lgpd_settings`, migração `0015`, só superadmin):
  nome/razão social e e-mail do Encarregado exibidos no Aviso de Privacidade
  (que passa a ler `GET /settings/legal`, público), e prazos de retenção em
  dias para **logins/accounting** (`radpostauth`, `cmd_acct`, `radacct`
  encerrado), **auditoria** (`app_audit_log`) e **usuários de autenticação
  desativados e sem uso**. Um expurgo oportunista roda no máximo 1×/dia
  (claim atômico via `last_purge_at`, disparado pelo `/health`); `0` desliga
  a exclusão automática daquele conjunto.

### Alterado

- **Textos do painel padronizados em pt-BR** (era uma mistura com pt-PT). A
  tela de contas do painel passou a se chamar **“Usuários do painel”** (vs
  **“Usuários de autenticação”**, as contas RADIUS/TACACS+).

- **Papéis (RBAC)**: o **operador** deixa de ver Auditoria e Grupos de usuário e
  de excluir usuários de autenticação e equipamentos (`DELETE` passa a exigir
  admin; escrever grupo idem). O **auditor** fica restrito à leitura de
  equipamentos e dos relatórios AAA — sem a área de usuários nem o log de
  auditoria. O aviso “ative o 2FA” passa a aparecer também para o operador.
- Menu lateral vira **gaveta sobreposta** em telas menores (backdrop, trava o
  scroll); área central mais larga (até 1600 px) e sem rolagem horizontal da
  página.

### Corrigido

- Modais renderizados via **portal no `<body>`** — “Notas de versão” e afins não
  ficam mais presos/espremidos dentro da sidebar (que usa `transform`).
- `index.html` servido com `Cache-Control: no-cache`, evitando SPA velha em
  cache após deploy.

## [0.4.0] — 2026-09-04

### Adicionado

- **Servidor TACACS+** (`tac_plus-ng`, serviço `tacacs`, porta `49/tcp`) ao lado
  do RADIUS. Autenticação/autorização/accounting de usuário resolvidos em tempo de
  request pelo **MAVIS** contra o mesmo MySQL (reusa `SSHA2-512-Password` e
  `radius_svc`); equipamentos e perfis vão para um arquivo gerado pelo painel e o
  daemon recarrega com `SIGHUP`.
- **Protocolo por equipamento** — no grupo de equipamentos (padrão `radius`) e no
  equipamento (em branco = herda): `radius` **ou** `tacacs`. **Chave TACACS+**
  separada e herdável (cifrada Fernet), como o segredo RADIUS. MikroTik segue só
  RADIUS (o RouterOS não tem cliente TACACS+); TACACS+ cobre Huawei/Juniper/Datacom.
- **Perfil de privilégio** ganha `priv-lvl` (0–15) e AV pairs extra para TACACS+.
- Accounting de comando do TACACS+ cai na tabela `cmd_acct` → aparece automático
  nas telas **Authorization** e **Accounting**.
- Migração `0008`; `docs/device-config/*` com trechos de config (Junos
  `tacplus-server`, VRP `hwtacacs-server`, DmOS `tacacs-server`); firewall `49/tcp`.

## [0.3.0] — 2026-09-03

### Adicionado

- **Relatórios divididos em três** no menu (antes só "Accounting"):
  - **Authentication** — tentativas de login (`radpostauth`), Accept/Reject.
  - **Authorization** — comandos executados nos equipamentos, com o IP de origem
    de quem executou.
  - **Accounting** — aba *Comandos* + aba *Sessões* (`radacct`, como antes).
  Filtros por usuário / NAS / período e export CSV em cada uma.
- **Contabilização de comandos** (`cmd_acct`, migração 0007): o site `default` do
  FreeRADIUS grava o comando quando o Accounting-Request o traz num VSA. Cisco /
  `shell:cmd=` funcionam direto; Huawei/Juniper/Datacom mapeiam o VSA real para
  `Pulse-Command` (ver `docs/RUNBOOK.md`). O comando entra com escape `=XX`
  (anti-injeção) e o backend reverte na leitura.
- **Fuso horário por Usuário do painel** (campo no cadastro, padrão
  `America/Sao_Paulo`). As datas da API passam a sair em UTC explícito e o painel
  converte na exibição (corrige o "3h adiantado").

## [0.2.0] — 2026-09-03

### Adicionado

- **Backup e restauração pelo painel** (Configuração → Backup e restauração, só
  superadmin). Exporta um `.sql` com esquema + dados de todas as tabelas (RADIUS,
  painel e `alembic_version`); opção de incluir ou não o histórico de accounting
  (`radacct`/`radpostauth`). A restauração recria o banco a partir do arquivo
  enviado, com confirmação explícita (`RESTAURAR`). Dump lógico feito em Python
  (pymysql) — não exige `mysqldump` na imagem do backend. Endpoints
  `GET /api/backup/export` e `POST /api/backup/import`; ambos registrados na
  auditoria. `gunicorn --timeout 180` para acomodar restaurações grandes.
- **Login administrativo MikroTik (MS-CHAPv2)**: o `radcheck` passa a receber
  também um `NT-Password` (MD4, sem texto claro) além do `SSHA2-512-Password`, e o
  virtual server `default` do FreeRADIUS ganhou `mschap` no authorize e
  `Auth-Type MS-CHAP` no authenticate. Huawei/Juniper/Datacom seguem por PAP.
  Usuários criados antes desta versão precisam de um **Redefinir senha** para
  ganhar o `NT-Password`.

### Corrigido

- **FreeRADIUS não recebia RADIUS externo**: o serviço só participava da rede
  `internal` (`internal: true`), então o Docker não entregava o tráfego publicado
  (`1812/1813 udp`) ao container. Anexado também à rede `edge`.

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
- **Usuários do painel** (papéis superadmin/admin/operator/auditor) e log de
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

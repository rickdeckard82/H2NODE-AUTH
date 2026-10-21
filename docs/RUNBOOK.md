# Runbook — Pulse RADIUS

## Subir / derrubar

```bash
make up        # produção-like
make dev       # desenvolvimento (+ adminer, portas expostas)
make down      # para tudo, mantém volumes
make clean     # para tudo e APAGA o banco (volumes)
make logs      # segue logs
make ps
```

## Banco

```bash
make migrate                       # alembic upgrade head
make revision m="add coluna x"     # nova migração autogerada
make seed                          # re-roda o seed idempotente
```

O `db/init/*` só roda na **primeira** criação do volume. Para recriar do zero:
`make clean && make up`.

## FreeRADIUS

```bash
# modo debug em foreground (muito verboso)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up freeradius

# validar config sem subir
docker compose exec freeradius freeradius -CX

# teste de autenticação
make test-radius u=<login> p='<senha>'

# accounting manual
docker compose exec freeradius radclient -x 127.0.0.1:1813 acct testing123 <<'EOF'
User-Name = "<login>"
Acct-Status-Type = Start
Acct-Session-Id = "s1"
NAS-IP-Address = <ip-do-nas>
EOF
```

Se um equipamento novo não autenticar logo após o cadastro:
1. confirme que o `NAS-IP-Address` do request == `app_equipment.mgmt_ip`;
2. confirme o *shared secret*;
3. como último recurso: `docker compose restart freeradius`.

## Troubleshooting rápido

| Sintoma | Verificar |
|---|---|
| `Access-Reject` com senha certa | `app_auth_user.is_active` / `expires_at`; log do `freeradius -X` |
| Sem VSA na resposta | perfil tem linha para o fabricante? `SELECT * FROM radgroupreply WHERE groupname='profile_<perfil>'` |
| VSA do fabricante errado | policy `vendor-authz`: o `mgmt_ip` do equipamento casa com o IP de origem? |
| `nas` não reconhecido | `SELECT * FROM nas WHERE nasname='<ip>'`; virtual server `dynamic_clients` nos logs |
| `Shared secret is incorrect` | equipamento sem segredo próprio → confira o **segredo padrão do fabricante** (página Fabricantes); trocar lá re-propaga para os equipamentos que herdam |
| 401 em loop no painel | relógio do host / `JWT_SECRET` mudou / cookies bloqueados (precisa HTTPS se `COOKIE_SECURE=true`) |
| Backend não sobe | `docker compose logs backend` — normalmente migração ou `DATABASE_URL` |

## Backup / restore

### Pelo painel (superadmin → Configuração → Backup e restauração)

- **Baixar backup**: gera um `.sql` com esquema + dados de todas as tabelas
  (RADIUS + painel + `alembic_version`). Caixa "incluir accounting" controla se
  `radacct`/`radpostauth` entram (desmarque para um arquivo pequeno de config).
- **Restaurar**: envia o `.sql`, digita `RESTAURAR` e confirma. **Destrutivo** —
  cada tabela é dropada e recriada a partir do arquivo. A sessão atual pode cair;
  refaça login. Endpoints: `GET /api/backup/export`, `POST /api/backup/import`.

O dump lógico é feito em Python (pymysql), não precisa do binário `mysqldump` no
container do backend. Restaure só num stack com o **mesmo `FERNET_KEY`**.

### Backup automático agendado por FTP/FTPS (inclusive Pulse Backup)

No mesmo menu, o quadro **Backup automático por FTP** envia todo dia, no horário e
fuso escolhidos, o mesmo dump do "Baixar backup" para um servidor FTP/FTPS:

- **Arquivo**: `pulse-radius-backup-AAAAMMDD-HHMMSS.sql.enc` (cifrado com a
  `FERNET_KEY`, padrão) ou `.sql.gz` (em claro, comprimido). Os dois são
  restauráveis direto em **Restaurar backup**.
- **Envio**: grava como `.part`, confere o tamanho (`SIZE`) e renomeia; depois
  apaga as cópias além de **Cópias mantidas**. A pasta é criada se não existir.
  Nada fica no servidor — o arquivo vai de uma pasta temporária para o FTP e é
  apagado; sobras de uma execução interrompida somem quando o worker reinicia.
- **Destino só de gravação (Pulse Backup)**: envia direto com o nome final, sem
  `SIZE`/`DELE`/`RNFR`, e não apaga nada — a retenção é a do servidor de backup.
  O dump traz o cabeçalho/rodapé no formato do `mysqldump`, então o Pulse Backup
  confere se ele chegou completo (no `.sql.gz`; o `.sql.enc` é só guardado).
- **Testar conexão** usa os dados do formulário sem salvar; **Executar agora**
  pede uma execução, que o worker pega em até `BACKUP_WORKER_INTERVAL_SECONDS`
  (30 s). Se o worker estava parado no horário, ainda roda até 6 h depois.
- Cada execução fica no resumo do quadro e na **Auditoria** (entidade
  `backup_schedule`, ações `backup_success`/`backup_error`, ator `sistema`).

Quem executa é o serviço `backup-worker` (mesma imagem do backend,
`python -m app.backup_worker`), que sobe por padrão e precisa de saída para o
servidor FTP. A senha FTP fica cifrada com a `FERNET_KEY` no banco. Logs:
`docker compose logs -f backup-worker`.

### Pela linha de comando (alternativa / automação)

```bash
# backup
docker compose exec db sh -c 'mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction radius' > backup-$(date +%F).sql

# restore (banco vazio)
cat backup-YYYY-MM-DD.sql | docker compose exec -T db sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" radius'
```

O serviço `db-backup` sobe **por padrão** (não precisa de `--profile`) e faz dump
periódico (`BACKUP_INTERVAL_SECONDS`, padrão 1 dia) no volume `db_backups`,
mantendo os últimos `BACKUP_KEEP` (padrão 14). Se `BACKUP_ENCRYPTION_KEY` estiver
definida no `.env` (gerada automaticamente por `make init`), cada dump sai cifrado
(`AES-256-CBC` via `openssl`) como `radius-<timestamp>.sql.enc`; sem a chave, sai em
texto claro e o log do serviço avisa a cada rodada. Para desligar em dev:
`docker compose up -d --scale db-backup=0`.

Restaurar um `.sql.enc` manualmente:

```bash
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 \
  -in radius-YYYYMMDD-HHMMSS.sql.enc -out radius.sql -pass env:BACKUP_ENCRYPTION_KEY
```

**Restore drill** (prova de verdade que o backup restaura, não só que ele existe):
`make restore-drill` (ou `./scripts/restore_drill.sh`) sobe um MySQL efêmero e
isolado, aplica o backup mais recente do volume `db_backups`, roda queries de
sanidade (contagem de tabelas, `app_system_user`, `app_manufacturer`, `radcheck`,
`nas`) e sai com código de erro se algo falhar — nunca toca no `db` real. Agende
isso num cron do host (ex.: mensal) e alerte se o exit code for != 0:

```cron
0 4 1 * * cd /opt/pulse-radius && ./scripts/restore_drill.sh >> /var/log/pulse-radius-restore-drill.log 2>&1
```

Itens críticos a guardar fora do host: os dumps **e** o `.env` (contém `FERNET_KEY` —
sem ela os segredos cifrados são irrecuperáveis — e `BACKUP_ENCRYPTION_KEY`, sem a
qual os `.sql.enc` são irrecuperáveis) e `JWT_SECRET`. O backup do painel (via UI)
também pode ser cifrado (opção marcada por padrão) com a mesma `FERNET_KEY` do
backend — o "Baixar backup" sob demanda **não substitui** o `db-backup`
automático; o backup agendado por FTP sim leva uma cópia para fora do host.

## Relatórios (Authentication / Authorization / Accounting)

- **Authentication** — tentativas de login (`radpostauth`): Access-Accept/Reject,
  com **protocolo** (RADIUS/TACACS+), **IP de origem** (de onde o técnico
  conectou — `Calling-Station-Id` no RADIUS, `rem-addr` no TACACS+; fica em
  branco se o equipamento não repassar esse dado) e **IP de destino** (o
  equipamento acessado). RADIUS grava direto pelo site `default`; TACACS+ é
  importado do `access.log` do tac_plus-ng (ver abaixo).
- **Authorization** — comandos executados (`cmd_acct`), com o IP de origem de quem
  executou.
- **Accounting** — aba *Comandos* (`cmd_acct`, sem o IP de origem) + aba *Sessões*
  (`radacct`: início/fim, bytes, duração).

As datas na API saem em UTC explícito; o painel converte para o **fuso de cada
Usuário do painel** (cadastro → *Fuso horário*, padrão `America/Sao_Paulo`).

### Contabilização de comandos (`cmd_acct`)

O site `default` (seção `accounting`) grava `cmd_acct` quando o Accounting-Request
traz o comando executado:

- **Cisco e a maioria dos gateways** (`Cisco-AVPair = "cmd=..."` / `"shell:cmd=..."`)
  funcionam sem ajuste.
- **Huawei / Juniper / Datacom / A10**: confirme o VSA real do seu firmware com
  `freeradius -X` num comando executado e mapeie-o para `Pulse-Command` logo no
  início do bloco em `radius/sites-available/default`, por ex.:

  ```
  if (&Huawei-Exec-Command) {           # troque pelo atributo REAL do seu firmware
      update control { &Pulse-Command := "%{Huawei-Exec-Command}" }
  }
  ```

O comando é gravado com escape `=XX` (proteção contra injeção); o backend reverte
na leitura. Grants: `radius_svc` tem `SELECT, INSERT` em `cmd_acct` (migração 0007
e `db/init/01_db_users.sh`).

## TACACS+ (tac_plus-ng)

Serviço `tacacs` (porta `49/tcp`). Cobre **Huawei / Juniper / Datacom / A10 / ZTE / Dell** que
falam TACACS+ — o **MikroTik não tem cliente TACACS+** e continua em RADIUS. O ZTE
e o Dell hoje só falam TACACS+ neste projeto (sem VSA RADIUS mapeado).

- **Autenticação/autorização** (usuário, senha, grupo): resolvidas em tempo de
  request pelo **MAVIS** (`tacacs/pulse_mavis.py`) contra o MySQL do painel
  (reusa `SSHA2-512-Password` do `radcheck` e `radius_svc`). Trocar um usuário de
  autenticação **não** exige reload.
- **Equipamentos + perfis**: o painel gera `/etc/tacacs-shared/pulse.cfg` (volume
  `tacacs_conf`, `include`d) e o container recarrega com `SIGHUP` ao detectar a
  mudança. Regerado ao salvar equipamento / grupo de equipamentos / perfil.
- **Accounting de comando**: o daemon grava
  `/var/log/tac_plus-ng/acct.log`; `tacacs/acct_import.py` (no mesmo container)
  segue o arquivo e insere em **`cmd_acct`** → aparece em *Authorization* e
  *Accounting* do painel.
- **Tentativas de login**: o daemon grava as autenticações de shell em
  `/var/log/tac_plus-ng/access.log`; `tacacs/authlog_import.py` segue o arquivo e
  insere em **`radpostauth`** com `protocol='tacacs'` → aparece em
  *Authentication*. Importa qualquer linha `<método> login succeeded/failed`
  (`shell`/`ascii`/`pap`/`chap`/`mschap`/`enable`/`ssh-key-hash`/`radius …` — o
  método varia por equipamento); as de autorização já vão para `cmd_acct`.
- **Protocolo por equipamento**: no cadastro do grupo (padrão `radius`) e do
  equipamento (em branco = herda). `radius` ⇒ vira cliente `nas`; `tacacs` ⇒ vira
  `host` no `pulse.cfg`. Alternar remove de um lado e adiciona no outro.

Debug ao vivo:

```bash
docker compose exec tacacs sh -c 'pkill tac_plus-ng; \
  /opt/tacplus/sbin/tac_plus-ng -d 2047 -D -f /etc/tac_plus-ng/tac_plus-ng.cfg'
# ou, testar só o MAVIS:
docker compose exec tacacs sh -c \
  'printf "0 TACPLUS\n4 <user>\n8 <senha>\n49 AUTH\n=\n" | python3 /opt/pulse/pulse_mavis.py'
```

## Rotação de segredos

- **`JWT_SECRET`**: trocar invalida todas as sessões do painel (todos re-logam). OK a qualquer momento.
- **`FERNET_KEY`**: NÃO troque sem migrar os campos cifrados. Procedimento: descriptografar
  com a chave antiga, recriptografar com a nova (script ad-hoc usando `app.core.crypto`).
- **Shared secret de equipamento**: editar no painel → reflete em `nas.secret` na hora;
  agende a troca no equipamento na mesma janela.

## Produção — checklist

### Aplicação (coberto pelo repositório)

- [ ] `.env` com senhas fortes e únicas (`make init` gera); `COOKIE_SECURE=true`; `PUBLIC_HOST` real.
- [ ] `FRONTEND_ORIGIN` = URL pública (https).
- [ ] `BACKUP_ENCRYPTION_KEY` definida (`make init` já gera) — sem ela o `db-backup` grava em texto claro.
- [ ] `make restore-drill` agendado no cron do host e alertando em caso de falha (ver "Backup / restore" acima).
- [ ] Ativar 2FA em toda conta `superadmin`/`admin` (menu do usuário → "Ativar 2FA"); o painel avisa quem ainda não ativou.
- [ ] `pip-audit` / `npm audit` sem vulnerabilidades abertas antes de cada release (ver `pyproject.toml` / `package.json`).

### Infraestrutura (fora do código — responsabilidade de quem opera o servidor)

- [ ] Certificado TLS real na borda (Nginx Proxy Manager/Caddy com Let's Encrypt, ou
      `proxy/tls/server.{crt,key}` reais se usar o profile `tls-proxy`); nunca sirva o
      painel em HTTP puro fora de `localhost`. Com `COOKIE_SECURE=true` o backend já
      manda `Strict-Transport-Security` sozinho; o profile `tls-proxy` também manda.
- [ ] SSH do servidor: `PasswordAuthentication no`, `PermitRootLogin no`, só chave —
      passo a passo em `docs/host-hardening.md`.
- [ ] Firewall do host (`ufw`/`nftables`): expor só a porta do proxy (443 ou `WEB_PORT`
      restrito ao IP do NPM) e `1812-1813/udp`/`49/tcp` restritos à rede de gerência dos
      equipamentos — comandos prontos em `docs/host-hardening.md`.
- [ ] Disco do host cifrado em repouso (LUKS/dm-crypt, ou já cifrado pelo provedor de
      nuvem) — o MySQL deste stack não faz encryption-at-rest por si só; sem disco
      cifrado, quem tiver acesso físico/aos discos lê `db_data` diretamente. Procedimento
      em `docs/host-hardening.md`.
- [ ] Monitorar `GET /api/metrics` e o `status` server do FreeRADIUS.

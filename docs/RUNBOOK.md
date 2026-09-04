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

### Pela linha de comando (alternativa / automação)

```bash
# backup
docker compose exec db sh -c 'mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction radius' > backup-$(date +%F).sql

# restore (banco vazio)
cat backup-YYYY-MM-DD.sql | docker compose exec -T db sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" radius'
```

Perfil `backup` (`docker compose --profile backup up -d`) sobe um sidecar que faz
dump periódico no volume `db_backups`.

Itens críticos a guardar fora do host: os dumps **e** o `.env` (contém `FERNET_KEY` —
sem ela os segredos cifrados são irrecuperáveis) e `JWT_SECRET`. O backup do painel
**não** inclui esses segredos.

## Relatórios (Authentication / Authorization / Accounting)

- **Authentication** — tentativas de login (`radpostauth`): Access-Accept/Reject.
- **Authorization** — comandos executados (`cmd_acct`), com o IP de origem de quem
  executou.
- **Accounting** — aba *Comandos* (`cmd_acct`, sem o IP de origem) + aba *Sessões*
  (`radacct`: início/fim, bytes, duração).

As datas na API saem em UTC explícito; o painel converte para o **fuso de cada
Utilizador do sistema** (cadastro → *Fuso horário*, padrão `America/Sao_Paulo`).

### Contabilização de comandos (`cmd_acct`)

O site `default` (seção `accounting`) grava `cmd_acct` quando o Accounting-Request
traz o comando executado:

- **Cisco e a maioria dos gateways** (`Cisco-AVPair = "cmd=..."` / `"shell:cmd=..."`)
  funcionam sem ajuste.
- **Huawei / Juniper / Datacom**: confirme o VSA real do seu firmware com
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

Serviço `tacacs` (porta `49/tcp`). Cobre **Huawei / Juniper / Datacom** que falam
TACACS+ — o **MikroTik não tem cliente TACACS+** e continua em RADIUS.

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

- [ ] `.env` com senhas fortes e únicas; `COOKIE_SECURE=true`; `PUBLIC_HOST` real.
- [ ] `FRONTEND_ORIGIN` = URL pública (https).
- [ ] Certificado TLS real em `proxy/tls/server.{crt,key}`.
- [ ] Backup automatizado do MySQL (cron/sidecar) + teste de restore.
- [ ] Firewall: expor só 443 ao público; 1812/1813/udp restrito à rede de gerência.
- [ ] Monitorar `GET /api/metrics` e o `status` server do FreeRADIUS.

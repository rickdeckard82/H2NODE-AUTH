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

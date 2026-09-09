# Deploy atrás de um reverse proxy externo (Nginx Proxy Manager)

Cenário: o servidor do Pulse RADIUS tem **IP privado**; outro servidor roda o
**Nginx Proxy Manager (NPM)** e publica o painel na internet/intranet com TLS e
domínio. Os equipamentos de rede falam RADIUS direto com o IP privado do servidor.

```
 navegador ──HTTPS──▶  NPM (outro servidor)  ──HTTP──▶  <IP-privado>:8080  (frontend: SPA + /api)
 equipamentos ──RADIUS/UDP──▶  <IP-privado>:1812 / :1813  (freeradius)
```

Neste modo o **proxy TLS embutido não é usado** (fica atrás do profile
`tls-proxy`). O container `frontend` é o entrypoint HTTP: serve a SPA e encaminha
`/api` para o backend.

## 1. Configuração no servidor do Pulse RADIUS

`.env` (a partir de `.env.example`):

```dotenv
# publicação HTTP para o NPM alcançar
WEB_PORT=8080
WEB_BIND=10.0.0.20          # IP privado do servidor (ou 0.0.0.0)

# URL pública que o NPM vai servir — usada no CORS
FRONTEND_ORIGIN=https://radius.suaempresa.com.br
COOKIE_SECURE=true          # o NPM entrega HTTPS ao navegador

# confie apenas no proxy do NPM para ler X-Forwarded-*
FORWARDED_ALLOW_IPS=10.0.0.30      # IP do servidor do NPM  (ou * para qualquer)

# segredos fortes
MYSQL_ROOT_PASSWORD=...
MYSQL_BACKEND_PASSWORD=...
MYSQL_RADIUS_PASSWORD=...
REDIS_PASSWORD=...
JWT_SECRET=...              # openssl rand -hex 32
FERNET_KEY=...              # openssl rand -base64 32 | tr '+/' '-_'
BOOTSTRAP_ADMIN_PASSWORD=...
```

`make init` gera todos esses valores de uma vez. Para não guardar `JWT_SECRET` /
`FERNET_KEY` no `.env`, deixe-os vazios e use o overlay de arquivos:
`make secrets && docker compose -f docker-compose.yml -f docker-compose.secrets.yml up -d`.

Subir (sem o profile `tls-proxy`):

```bash
docker compose build
docker compose up -d
docker compose ps        # frontend deve expor 0.0.0.0/<IP>:8080->80
```

## 2. Firewall do servidor Pulse RADIUS

| Porta | Origem permitida | Uso |
|---|---|---|
| `8080/tcp` (WEB_PORT) | **só o IP do servidor do NPM** | painel + API |
| `1812/udp`, `1813/udp` | rede de gerência dos equipamentos | RADIUS auth + accounting |
| `49/tcp` | rede de gerência dos equipamentos | TACACS+ (Huawei/Juniper/Datacom/A10) — omita se não usar |
| `22/tcp` | administração | SSH |

Tudo o mais fechado. `3306` (MySQL) e `8000` (backend) **não** são publicados no modo padrão.

## 3. Proxy Host no Nginx Proxy Manager

**Details**
- Domain Names: `radius.suaempresa.com.br`
- Scheme: `http`
- Forward Hostname / IP: `10.0.0.20` (IP privado do servidor Pulse RADIUS)
- Forward Port: `8080`
- Cache Assets: opcional
- **Block Common Exploits**: ligado
- **Websockets Support**: pode deixar ligado (a app não usa, mas não atrapalha)

**SSL**
- SSL Certificate: solicite um Let's Encrypt (ou use um já existente)
- **Force SSL**: ligado
- **HTTP/2 Support**: ligado
- **HSTS Enabled**: ligado

**Advanced** — cole isto. O `$remote_addr` (em vez de `$proxy_add_x_forwarded_for`)
faz o NPM **substituir** o X-Forwarded-For pelo IP real do cliente, impedindo que
um cliente forje o IP que aparece na auditoria e no bloqueio de login:

```nginx
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-For  $remote_addr;
proxy_set_header Host             $host;
client_max_body_size 2m;
```

E no `.env` do servidor, defina `FORWARDED_ALLOW_IPS` com o **IP do servidor do
NPM** (não deixe `*`).

Não é preciso criar "Custom Location" para `/api` — o container `frontend` já
roteia `/api` para o backend internamente.

## 4. Equipamentos (NAS)

Aponte cada equipamento para o **IP privado do servidor Pulse RADIUS** nas portas
padrão, com o *shared secret* cadastrado no painel (no equipamento ou herdado do
grupo/fabricante):

```
auth   : 10.0.0.20:1812
acct   : 10.0.0.20:1813
secret : <o cadastrado no painel>
```

Snippets por fabricante em [device-config/](device-config/). Garanta que o
`NAS-IP-Address` / IP de origem do pacote seja o mesmo `mgmt_ip` cadastrado — a
resolução de cliente e a tradução de VSA usam o IP de origem do pacote UDP.

## 5. Verificação

```bash
# do servidor do NPM (ou de dentro da rede):
curl -s http://10.0.0.20:8080/api/health          # {"status":"ok"}
curl -skI https://radius.suaempresa.com.br         # 200, via NPM

# RADIUS, de dentro do servidor Pulse RADIUS:
docker compose exec freeradius radtest -t pap <user> <senha> 127.0.0.1:1812 0 testing123
```

Login no painel: `https://radius.suaempresa.com.br` com `BOOTSTRAP_ADMIN_*`.

## Observações

- **CoA / Disconnect (3799/udp)** está fora do escopo desta versão; se for
  habilitar depois, libere também essa porta *do servidor para os equipamentos*.
- Se o NPM e o Pulse RADIUS ficarem no mesmo host Docker, dá para colocá-los na
  mesma rede e apontar o NPM para `frontend:80` em vez de `<IP>:8080`.
- Backups do MySQL: `docker compose --profile backup up -d db-backup` (ver
  [RUNBOOK.md](RUNBOOK.md)).

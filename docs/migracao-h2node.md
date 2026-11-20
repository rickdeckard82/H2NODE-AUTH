# Migração: Pulse RADIUS → H2NODE Auth

O projeto mudou de nome na versão **1.2.0**. Para os equipamentos nada muda: RADIUS
(1812/1813 udp) e TACACS+ (49/tcp) continuam no mesmo IP, com os mesmos segredos,
usuários, grupos e perfis. A troca é só no servidor, e leva o tempo de recriar os
containers.

## 1. Servidor

Na pasta do repositório (ex.: `/opt/pulse-radius` — a pasta pode manter o nome antigo):

```bash
git pull
sudo ./scripts/migrar-h2node.sh      # mostra o plano e pede confirmação
```

O script:

- acrescenta `VOLUME_PREFIX=pulse-radius` ao `.env` (os volumes passaram a ter nome
  fixo, `${VOLUME_PREFIX}_db_data` etc.), mantendo **o mesmo banco**, os backups do
  `db-backup`, os logs e a config gerada do TACACS+;
- derruba os containers do projeto compose antigo (`docker compose -p pulse-radius down`,
  **sem** `-v`) e sobe o projeto `h2node-auth`.

O `.env` original fica copiado em `.env.antes-h2node.<data>`. O `docker compose` pode
avisar que os volumes foram criados por outro projeto: é esperado.

O banco (`MYSQL_DATABASE`, padrão `radius`) e os usuários do MySQL não mudam de nome.
As regras do ufw (1812:1813/udp, 49/tcp, porta do painel) continuam valendo.

> Ambiente de teste com o overlay de dev: depois do script, suba com `make dev` como
> antes (o script sobe só o `docker-compose.yml`).

## 2. Conferir

```bash
docker compose ps                                   # tudo "healthy"
docker compose logs tacacs | grep h2node-tacacs     # "migrando .../pulse.cfg -> .../h2node.cfg" no 1º start
docker compose logs backend | grep tacacs_config_synced
```

Faça um login de teste em um equipamento RADIUS e em um TACACS+ e veja as linhas em
**Authentication** e **Accounting** no painel.

## O que mudou de nome

| Antes (Pulse RADIUS) | Agora (H2NODE Auth) | Observação |
|---|---|---|
| projeto compose `pulse-radius` | `h2node-auth` | volumes mantidos com `VOLUME_PREFIX=pulse-radius` |
| `/etc/tacacs-shared/pulse.cfg` | `/etc/tacacs-shared/h2node.cfg` | copiado no 1º start; o backend o regrava a cada start |
| atributos internos `Pulse-Command`, `Pulse-Command-Action`, `Pulse-Origin-IP`, `Pulse-Client-IP` | `H2NODE-*` (mesmos números) | nunca vão para o equipamento |
| `pulse-radius-backup-*.sql(.enc\|.gz)` | `h2node-auth-backup-*` | antigos continuam restauráveis |
| emissor do 2FA "Pulse RADIUS" | "H2NODE Auth" | só para novos cadastros |

Se você mapeou o comando do firmware para `Pulse-Command` num `update` do
`radius/sites-available/default` (command accounting de Huawei, A10, Juniper…), troque
para `H2NODE-Command` ao resolver o conflito do `git pull`.

## O que continua com o nome antigo (de propósito)

- Backups gerados pelo Pulse RADIUS (marcador `-- Pulse RADIUS backup v1`, cifra
  `PULSEENC1`) continuam aceitos em **Restaurar backup**.
- No backup por FTP, as cópias antigas `pulse-radius-backup-*` continuam na pasta e
  entram na retenção junto com as novas, pela data — vão sendo apagadas sozinhas.
- Os aplicativos autenticadores (2FA) já configurados mostram "Pulse RADIUS" até o
  usuário refazer o cadastro; os códigos continuam válidos.
- Os nomes de template/servidor nos equipamentos (ex.: `radius-server template PULSE`
  no Huawei) são só rótulos locais: não precisam mudar. A documentação nova usa `H2NODE`.

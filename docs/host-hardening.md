# Hardening do host — SSH, firewall e disco (fora do escopo do Docker Compose)

Este documento cobre a parte da segurança que **não pode ser resolvida em código**:
a configuração do sistema operacional do servidor onde o H2NODE Auth roda. Ninguém deve rodar isto automaticamente — revise cada
comando antes de aplicar, principalmente os de SSH (um erro aqui pode trancar
seu próprio acesso remoto). Testado para Debian/Ubuntu; adapte para sua distro.

## 1. SSH — só chave, sem root

```bash
# gere uma chave no seu computador (não no servidor) se ainda não tiver:
ssh-keygen -t ed25519 -C "seu-nome@h2node-auth"
ssh-copy-id usuario@servidor

# no servidor, edite /etc/ssh/sshd_config:
sudo sed -i \
  -e 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' \
  -e 's/^#\?PermitRootLogin.*/PermitRootLogin no/' \
  -e 's/^#\?PubkeyAuthentication.*/PubkeyAuthentication yes/' \
  /etc/ssh/sshd_config

# valide a sintaxe ANTES de reiniciar (evita ficar trancado de fora)
sudo sshd -t

# só reinicie depois de confirmar que sua chave já funciona numa 2ª sessão aberta
sudo systemctl restart ssh
```

Opcional, mas recomendado: `fail2ban` para banir IPs com tentativas repetidas de
força bruta contra o próprio SSH (`apt install fail2ban`, perfil `sshd` já vem
ativo por padrão).

## 2. Firewall — só as portas do `docs/deploy-behind-npm.md`

```bash
sudo apt install ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow OpenSSH                      # ou a porta custom do seu sshd_config

# painel: só o IP do reverse proxy (Nginx Proxy Manager), nunca aberto ao mundo
sudo ufw allow from <IP-DO-NPM> to any port 8080 proto tcp

# RADIUS/TACACS+: freeradius e tacacs usam network_mode: host no docker-compose, então
# o `ufw allow` comum filtra por origem (não precisa de ufw-docker para eles).
# RADIUS: só a rede de gerência dos equipamentos
sudo ufw allow from <CIDR-DA-REDE-DE-GERENCIA> to any port 1812 proto udp
sudo ufw allow from <CIDR-DA-REDE-DE-GERENCIA> to any port 1813 proto udp

# TACACS+ (se algum equipamento usar TACACS+)
sudo ufw allow from <CIDR-DA-REDE-DE-GERENCIA> to any port 49 proto tcp

sudo ufw enable
sudo ufw status verbose
```

Se usar o profile `tls-proxy` embutido (sem NPM externo), libere `443/tcp` (e
`80/tcp` só para o redirect) publicamente em vez da porta 8080 restrita.

## 3. Disco cifrado em repouso

O MySQL deste stack **não** faz encryption-at-rest por conta própria (sem
keyring plugin/TDE configurado) — a proteção vem do disco do host. Duas opções:

- **Provedor de nuvem**: a maioria (AWS EBS, GCP Persistent Disk, Azure Managed
  Disk, etc.) oferece "disco cifrado" como opção na criação da VM — ligue isso
  antes de colocar dados em produção; migrar depois exige recriar o disco.
- **Servidor próprio / bare metal**: cifre a partição de dados com LUKS antes de
  montar o volume Docker nela:

```bash
# EXEMPLO — adapte o device (/dev/sdX) ao seu ambiente; isto APAGA o conteúdo atual
sudo cryptsetup luksFormat /dev/sdX
sudo cryptsetup open /dev/sdX h2node_data
sudo mkfs.ext4 /dev/mapper/h2node_data
sudo mkdir -p /mnt/h2node-data
sudo mount /dev/mapper/h2node_data /mnt/h2node-data
```

Depois, aponte o volume `db_data` do `docker-compose.yml` para um bind mount
dentro de `/mnt/h2node-data` (em vez do volume nomeado padrão do Docker), e
configure `/etc/crypttab` para desbloquear o disco no boot (com chave em TPM,
se disponível, para reinício sem digitação manual — ou aceite que o servidor
precisa de intervenção manual após reboot).

## Checklist rápido

- [ ] `sshd -t` validado, chave testada numa 2ª sessão, **depois** `PasswordAuthentication no`.
- [ ] `ufw status` mostra só as portas da tabela acima, com origem restrita.
- [ ] `fail2ban` ativo no perfil `sshd` (opcional, recomendado).
- [ ] Disco de dados cifrado (nuvem: opção do provedor; próprio: LUKS).

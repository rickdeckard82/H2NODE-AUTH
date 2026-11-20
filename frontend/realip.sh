#!/bin/sh
# Roda no start do nginx (/docker-entrypoint.d). Gera um `set_real_ip_from` para
# cada IP/CIDR de FORWARDED_ALLOW_IPS (lista separada por vírgula): só desses
# proxies o X-Forwarded-For é aceito como IP do cliente. Vazio ou "*" (valor
# antigo do .env) => faixas privadas, onde fica um reverse proxy da LAN (NPM) e o
# proxy TLS embutido; um cliente vindo da internet não consegue forjar o IP.
set -e
list="${FORWARDED_ALLOW_IPS:-*}"
[ "$list" = "*" ] && list="10.0.0.0/8,172.16.0.0/12,192.168.0.0/16,127.0.0.1,fc00::/7"
: > /etc/nginx/realip.conf
for ip in $(echo "$list" | tr ',' ' '); do
  echo "set_real_ip_from $ip;" >> /etc/nginx/realip.conf
done

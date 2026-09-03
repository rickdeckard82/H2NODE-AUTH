#!/bin/sh
# Gera um certificado self-signed se nenhum foi montado em /etc/nginx/tls.
# Em produção, monte server.crt / server.key reais nesse diretório.
set -e

TLS_DIR=/etc/nginx/tls
mkdir -p "$TLS_DIR"

if [ ! -f "$TLS_DIR/server.crt" ] || [ ! -f "$TLS_DIR/server.key" ]; then
  echo "[proxy] gerando certificado self-signed para ${PUBLIC_HOST:-localhost}"
  openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
    -keyout "$TLS_DIR/server.key" -out "$TLS_DIR/server.crt" \
    -subj "/CN=${PUBLIC_HOST:-localhost}" \
    -addext "subjectAltName=DNS:${PUBLIC_HOST:-localhost},DNS:localhost,IP:127.0.0.1"
fi

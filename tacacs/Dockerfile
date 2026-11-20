# ─────────────────────────────────────────────────────────────
# tac_plus-ng (Marc J. Huber, event-driven-servers) + MAVIS Python.
# Não há imagem oficial — compilamos a partir de um commit pinado.
# ─────────────────────────────────────────────────────────────
FROM debian:trixie-slim AS build

# O repositório não publica tags; pinamos o commit de master.
# Mova o SHA quando for atualizar de propósito.
ARG EDS_REF=3a7b593f202a7d5f7c60303a60f9869bcab51339

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential ca-certificates git libssl-dev libpcre2-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /src
# O wrapper Makefile chama `gmake`; no Debian `make` já é GNU make.
RUN ln -sf "$(command -v make)" /usr/local/bin/gmake \
 && git clone https://github.com/MarcJHuber/event-driven-servers.git . \
 && git checkout "${EDS_REF}" \
 && ./configure tac_plus-ng --prefix=/opt/tacplus \
 && make -j"$(nproc)" \
 && make install

# ─────────────────────────────────────────────────────────────
FROM debian:trixie-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      libssl3 libpcre2-8-0 python3 python3-pymysql python3-cryptography inotify-tools \
 && rm -rf /var/lib/apt/lists/* \
 && useradd -r -u 10002 -s /usr/sbin/nologin tacplus \
 && mkdir -p /etc/tacacs-shared /var/log/tac_plus-ng \
 && chown tacplus:tacplus /var/log/tac_plus-ng

COPY --from=build /opt/tacplus /opt/tacplus
ENV PATH="/opt/tacplus/sbin:/opt/tacplus/bin:${PATH}"

# password.py é stdlib puro (sem dependências do app) — usado pelo MAVIS.
COPY backend/app/services/password.py /opt/h2node/password.py
COPY tacacs/h2node_mavis.py           /opt/h2node/h2node_mavis.py
COPY tacacs/acct_import.py            /opt/h2node/acct_import.py
COPY tacacs/authlog_import.py         /opt/h2node/authlog_import.py
COPY tacacs/tac_plus-ng.cfg           /etc/tac_plus-ng/tac_plus-ng.cfg
COPY tacacs/entrypoint.sh             /usr/local/bin/h2node-tacacs-entrypoint.sh
RUN chmod +x /usr/local/bin/h2node-tacacs-entrypoint.sh

EXPOSE 49/tcp
ENTRYPOINT ["/usr/local/bin/h2node-tacacs-entrypoint.sh"]

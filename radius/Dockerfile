FROM freeradius/freeradius-server:3.2.7

# O driver rlm_sql_mysql já vem na imagem oficial.
# Copiamos apenas os overrides de configuração.

COPY mods-available/sql                 /etc/raddb/mods-available/sql
COPY sites-available/default            /etc/raddb/sites-available/default
COPY sites-available/dynamic-clients    /etc/raddb/sites-available/dynamic-clients
COPY policy.d/vendor-authz              /etc/raddb/policy.d/vendor-authz
COPY clients.conf                       /etc/raddb/clients.conf
COPY dictionary.local                   /etc/raddb/dictionary.local
COPY entrypoint.sh                      /usr/local/bin/h2node-entrypoint.sh

RUN set -eux; \
    # habilita sql + acct_unique + virtual server de clientes dinâmicos
    ln -sf ../mods-available/sql             /etc/raddb/mods-enabled/sql; \
    ln -sf ../mods-available/acct_unique     /etc/raddb/mods-enabled/acct_unique; \
    ln -sf ../sites-available/dynamic-clients /etc/raddb/sites-enabled/dynamic-clients; \
    # remove o que não usamos (login administrativo é só PAP/CHAP)
    rm -f /etc/raddb/mods-enabled/eap /etc/raddb/sites-enabled/inner-tunnel; \
    # inclui o dicionário local a partir do dicionário raiz
    printf '\n$INCLUDE dictionary.local\n' >> /etc/raddb/dictionary; \
    chmod +x /usr/local/bin/h2node-entrypoint.sh

ENTRYPOINT ["/usr/local/bin/h2node-entrypoint.sh"]
CMD ["freeradius", "-f", "-l", "stdout"]

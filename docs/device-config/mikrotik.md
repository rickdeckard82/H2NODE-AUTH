# Mikrotik (RouterOS) — apontar para o Pulse RADIUS

```
/radius
add service=login address=10.0.0.254 secret=<shared-secret-cadastrado-no-painel> \
    authentication-port=1812 accounting-port=1813 timeout=1s

/user aaa
set use-radius=yes accounting=yes interim-update=5m default-group=read
```

## Autorização

RouterOS mapeia o VSA `Mikrotik-Group` (26/14988/3) para um **group** local.
Os grupos `full`, `write` e `read` já existem por padrão.

| Atributo (fabricante Mikrotik no painel) | Valor |
|---|---|
| `Mikrotik-Group` | `full` (admin) / `write` (operador) / `read` (leitura) |

`default-group` é o fallback se o RADIUS não retornar `Mikrotik-Group`.
Para forçar o IP de origem igual ao `mgmt_ip` cadastrado, use uma rota/`src-address`
apropriada ou configure `/radius` com `src-address=10.0.0.1`.

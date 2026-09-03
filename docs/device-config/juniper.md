# Juniper (JUNOS) — apontar para o Pulse RADIUS

```
set system radius-server 10.0.0.254 port 1812
set system radius-server 10.0.0.254 accounting-port 1813
set system radius-server 10.0.0.254 secret <shared-secret-cadastrado-no-painel>
set system radius-server 10.0.0.254 source-address 10.0.0.1

set system authentication-order [ radius password ]
set system accounting events [ login change-log interactive-commands ]
set system accounting destination radius server 10.0.0.254 secret <secret>
```

## Autorização — login classes

O JUNOS não aceita "nível" numérico via RADIUS; ele mapeia o atributo
`Juniper-Local-User-Name` (VSA 26/2636/1) para uma **login class** definida localmente.
Crie as classes e use o mesmo nome no perfil de privilégio do painel:

```
set system login class super-user permissions all
set system login class operator  permissions [ view view-configuration clear network reset trace ]
set system login class read-only permissions [ view view-configuration ]
```

| Atributo (fabricante Juniper no painel) | Valor |
|---|---|
| `Juniper-Local-User-Name` | `super-user` / `operator` / `read-only` |

Um usuário "template" local casa a classe:

```
set system login user remote-radius class super-user
```

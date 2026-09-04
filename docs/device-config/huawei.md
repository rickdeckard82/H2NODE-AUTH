# Huawei (VRP) — apontar para o Pulse RADIUS

`10.0.0.254` = IP do host que roda o container `freeradius`.

```
radius-server template PULSE
 radius-server authentication 10.0.0.254 1812 weight 80
 radius-server accounting 10.0.0.254 1813 weight 80
 radius-server shared-key cipher <shared-secret-cadastrado-no-painel>
#
aaa
 authentication-scheme SCH_RADIUS
  authentication-mode radius local
 authorization-scheme SCH_RADIUS
  authorization-mode if-authenticated
 accounting-scheme ACC_RADIUS
  accounting-mode radius
 domain default_admin
  authentication-scheme SCH_RADIUS
  accounting-scheme ACC_RADIUS
  radius-server PULSE
#
user-interface vty 0 4
 authentication-mode aaa
 protocol inbound ssh
```

## Autorização

O perfil de privilégio no painel deve conter, para o fabricante **Huawei**:

| Atributo | Valor (exemplo) |
|---|---|
| `Huawei-Exec-Privilege` | `15` (admin) / `3` (operador) / `1` (leitura) |

Opcionalmente `Service-Type = Administrative-User`. O `NAS-IP-Address` que o
equipamento envia precisa ser exatamente o `mgmt_ip` cadastrado — force com:

```
radius-server template PULSE
 radius-attribute nas-ip-address 10.0.0.1
```

## Contabilização de comandos

Habilite o *command accounting* apontando para o Pulse e, no
`radius/sites-available/default` (bloco `accounting`), mapeie o VSA de comando
do seu firmware para `Pulse-Command` — confirme o nome exato com
`freeradius -X` num comando real. Ver `docs/RUNBOOK.md` → "Contabilização de
comandos".

## HWTACACS (alternativa ao RADIUS)

O tac_plus-ng do Pulse atende HWTACACS (variante Huawei do TACACS+). No painel:
grupo **Huawei** → *Protocolo AAA* = `tacacs` + *Chave TACACS+*. No VRP:

```
hwtacacs-server template PULSE
 hwtacacs-server authentication 10.0.0.254
 hwtacacs-server authorization 10.0.0.254
 hwtacacs-server accounting 10.0.0.254
 hwtacacs-server shared-key cipher <chave-cadastrada>
 hwtacacs-server source-ip 10.0.0.1          # = mgmt_ip
aaa
 authentication-scheme sch-tac
  authentication-mode hwtacacs
 authorization-scheme sch-tac
  authorization-mode hwtacacs
 accounting-scheme acc-tac
  accounting-mode hwtacacs
```

Nível de privilégio e comandos: ver a tela **Authorization / Accounting**.

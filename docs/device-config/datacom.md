# Datacom (DmOS) — apontar para o H2NODE Auth

```
config
 aaa server radius H2NODE host 10.0.0.254
  shared-secret "<shared-secret-cadastrado-no-painel>"
  authentication
  accounting
 !
 aaa authentication order [radius local]
commit
```

> `source interface` no RADIUS do DmOS só aceita Loopback ou L3 **sem** VRF.

## Autorização

O DmOS tem 3 níveis: `admin` > `config` > `audit`. O atributo/numeração exatos
para mapear via RADIUS **variam por versão** — confira o `dictionary.datacom` do
fornecedor (ou o Command Reference da sua release).

Este projeto embarca em `radius/dictionary.local` uma definição de referência
(`VENDOR Datacom 3709`, `Datacom-Privilege-Level` inteiro). Ajuste-a para bater
com o dicionário da sua release e configure o perfil de privilégio no painel:

| Atributo (fabricante Datacom no painel) | Valor de referência |
|---|---|
| `Datacom-Privilege-Level` | `15` (admin) / `10` (config) / `1` (audit) |

Se a sua release usar outro atributo (ex.: `Service-Type`, ou um VSA nomeado
diferente), basta editar a linha do fabricante Datacom no editor de perfis —
nada no FreeRADIUS precisa mudar além do dicionário.

## Contabilização de comandos

Se o DmOS enviar o comando executado num Accounting-Request, mapeie o atributo
para `H2NODE-Command` no `radius/sites-available/default` (bloco `accounting`) —
confirme o nome com `freeradius -X`. Ver `docs/RUNBOOK.md`.

## TACACS+ (alternativa ao RADIUS)

No painel: grupo **Datacom** → *Protocolo AAA* = `tacacs` + *Chave TACACS+*. No
DmOS:

```
tacacs-server host 10.0.0.254 key <chave-cadastrada>
aaa authentication login default group tacacs local
aaa authorization commands default group tacacs
aaa accounting commands default start-stop group tacacs
```

O `priv-lvl` do perfil vira o nível de acesso; os comandos aparecem em
**Authorization / Accounting** do painel.

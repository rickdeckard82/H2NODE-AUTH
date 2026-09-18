# ZTE ZXAN (OLTs Titan C6xx — C600/C610/C620/C650) — apontar para o Pulse TACACS+

Cobre a linha **Titan C6xx** (GPON/XGS-PON). Hoje o fabricante **ZTE** no
painel só está preparado para **TACACS+** — não há VSA RADIUS mapeado (o
grupo existe como `vendor_kind=zte`, mas a policy `vendor-authz` não filtra
nada para ele; se algum dia for necessário RADIUS, é só adicionar o VSA real
do seu firmware em `radius/dictionary.local` e um `case "zte"` na policy).

No painel: grupo **ZTE** → *Protocolo AAA* = `tacacs` + *Chave TACACS+*.
`10.0.0.254` = IP do host que roda o container `tacacs` (tac_plus-ng).

## Autenticação via TACACS+

A CLI ZXAN configura AAA por **templates** com indireção em dois níveis
(usuário → template `1..N` → template `aaa-authentication`/`aaa-authorization`
`2001..N`). O manual disponível documenta o fluxo completo para AAA **local**;
para apontar para um servidor TACACS+ o padrão é trocar o tipo do template e
declarar o servidor:

```
ZXAN(config)#tacacs-server host 10.0.0.254 key <chave-cadastrada-no-painel>

ZXAN(config)#aaa-authentication-template 2002
ZXAN(config-aaa-authen-template)#aaa-authentication-type tacacs local
ZXAN(config-aaa-authen-template)#exit

ZXAN(config)#aaa-authorization-template 2002
ZXAN(config-aaa-author-template)#aaa-authorization-type tacacs local
ZXAN(config-aaa-author-template)#exit

ZXAN(config)#system-user
ZXAN(config-system-user)#authentication-template 1
ZXAN(config-system-user-authen-temp)#bind aaa-authentication-template 2002
ZXAN(config-system-user-authen-temp)#exit
ZXAN(config-system-user)#authorization-template 1
ZXAN(config-system-user-author-temp)#bind aaa-authorization-template 2002
```

> `tacacs local` deixa o login local como fallback se o Pulse não responder —
> mesma lógica do `radius local` usado nos outros fabricantes. Confirme a
> palavra-chave exata (`tacacs`, `tacplus` ou `hwtacacs`, dependendo da
> versão de firmware) com `?` na CLI antes de aplicar em produção — a fonte
> usada para este guia documenta apenas o fluxo local em detalhe.

## Autorização e nível de privilégio

O TACACS+ do Pulse é **agnóstico de fabricante**: o nível de acesso e os AV
pairs vêm do perfil de privilégio cadastrado no painel, não de um VSA por
vendor. Configure no perfil:

| Campo do perfil (painel) | Uso |
|---|---|
| `priv-lvl` (TACACS+) | Nível de privilégio aplicado no login — mapeie para o `local-privilege-level` equivalente do usuário ZXAN (ex.: `15` = acesso total) |
| AV pairs extras | Uma por linha, ex. `shell:roles=...`, se o seu firmware/menu exigir |

Não é necessário nenhum VSA `ZTE-*` — o `tac_plus-ng` já entrega `priv-lvl` e
AV pairs pelo protocolo TACACS+ padrão.

## Contabilização de comandos

Habilite accounting de comando apontando para o servidor TACACS+ do painel; a
tela **Accounting** mostra os comandos executados. Confirme a sintaxe exata de
`aaa accounting` da sua versão de firmware com `?` na CLI — não confirmada na
documentação disponível para este guia.

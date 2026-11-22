# Dell EMC Networking (N1524 / N-Series, OS6) — apontar para o H2NODE Auth (TACACS+)

Validado em um **N1524 (firmware 6.6.0.2)**. Hoje o fabricante **Dell** no painel
só está preparado para **TACACS+** — não há VSA RADIUS mapeado (o grupo existe como
`vendor_kind=dell`, mas a policy `vendor-authz` não filtra nada para ele).

No painel: grupo **Dell** → *Protocolo AAA* = `tacacs` + *Chave TACACS+*.
`10.0.0.254` = IP do host que roda o container `tacacs` (tac_plus-ng).

## Configuração no switch

```
configure
tacacs-server host 10.0.0.254
 timeout 30
 key "<chave-cadastrada-no-painel>"
exit

aaa authentication login "TACACS" tacacs local
aaa authentication enable "TACP" tacacs
aaa accounting commands "dfltCmdList" start-stop tacacs

line ssh
 login authentication TACACS
 enable authentication TACP
 accounting commands default
exit
```

- `tacacs local` deixa o usuário local (`username ... privilege 15`) como fallback
  se o H2NODE Auth não responder.
- A lista `TACACS` vale para o login; `TACP` para o `enable` (que também passa
  pelo TACACS+). Aplique também em `line console` / `line telnet` se usar.
- O H2NODE Auth precisa estar com o IP do switch cadastrado como equipamento do grupo
  Dell (use o IP da interface de gerência, ex.: a `interface vlan` da rede de gerência).

## Autorização e nível de privilégio

O TACACS+ do H2NODE Auth é agnóstico de fabricante: o `priv-lvl` do perfil de privilégio
(15 / 10 / 1) é entregue no login. Não é necessário nenhum VSA `Dell-*`.

## Contabilização de comandos

`aaa accounting commands "dfltCmdList" start-stop tacacs` envia cada comando
executado; eles aparecem em **Authorization / Accounting** do painel.

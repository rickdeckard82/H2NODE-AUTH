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

O `enable` usa a **mesma senha do login**. Por padrão, cada perfil gera
`enable <nível> = login` até o seu priv-lvl (ex.: `admin-full` → `enable 15`). Perfis
de nível 0/1 não têm enable e a tentativa é recusada.

Dois campos do perfil de privilégio (seção TACACS+) mudam isso:

- **Nível de enable (TACACS+)**: vazio = comportamento acima. De 1 a 15, libera
  `enable <valor>` independente do priv-lvl; `0` = sem enable.
- **Comandos permitidos (regex, um por linha)**: vazio = todo comando é permitido.
  Preenchido, só passa o comando que casar com alguma regex; o resto é negado.
  Linhas vazias e iniciadas com `#` são ignoradas. A regex recebe o comando **com os
  argumentos**, separados por espaço (ex.: `show running-config`, `terminal length 0`).
  Escreva `/` e `"` como `\/` e `\"`; o painel recusa a regex sem escape.

### Perfil `noc-leitura` (agente de monitoramento)

O OS6 exige modo privilegiado até para `show interfaces status` ou `show process cpu`.
O perfil interno `noc-leitura` entrega priv-lvl 1 no login, libera `enable 15` e só
autoriza comandos de leitura:

```
^show( |$)
^terminal length
^(exit|quit)$
```

Use esse perfil para o usuário do agente (ex.: `noc-ro`) em vez de `admin-full`.
A lista de comandos só tem efeito com a autorização de comandos ligada no switch:

```
configure
aaa authorization commands "TACACS-CMD" tacacs none
line ssh
authorization commands TACACS-CMD
exit
exit
```

> **Atenção:** a autorização de comandos vale para **todos** os usuários do switch
> que entram pela `line ssh`, não só para o `noc-ro`. Todo comando passa a ser
> consultado no H2NODE Auth. Aplique com uma **segunda sessão aberta** (usuário local
> ou console) para poder desfazer (`no authorization commands`) se algo bloquear.

## Contabilização de comandos

`aaa accounting commands "dfltCmdList" start-stop tacacs` envia cada comando
executado; eles aparecem em **Authorization / Accounting** do painel.

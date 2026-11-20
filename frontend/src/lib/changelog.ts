export const APP_VERSION = "1.2.0";

export interface ChangelogEntry {
  version: string;
  date: string;
  changes: string[];
}

/** Mais recente primeiro. */
export const CHANGELOG: ChangelogEntry[] = [
  {
    version: "1.2.0",
    date: "2026-11-20",
    changes: [
      "O Pulse RADIUS agora se chama H2NODE Auth: nome, logotipo animado e ícones novos no painel, nos e-mails e no 2FA. Nada muda para os equipamentos: RADIUS (1812/1813) e TACACS+ (49) continuam nos mesmos endereços, com os mesmos segredos, usuários e perfis.",
      "Servidor: scripts/migrar-h2node.sh passa a instalação para o projeto h2node-auth mantendo o mesmo banco, os backups e a config do TACACS+ (VOLUME_PREFIX=pulse-radius). Veja docs/migracao-h2node.md.",
      "Backups: os arquivos passam a se chamar h2node-auth-backup-*. Backups antigos do Pulse RADIUS (.sql, .sql.gz e .sql.enc) continuam restauráveis, e as cópias antigas no FTP entram na retenção pela data.",
      "2FA: aplicativos autenticadores já configurados continuam valendo; só os novos cadastros aparecem como “H2NODE Auth”.",
      "Fabricante Dell (N-Series) via TACACS+; freeradius e tacacs em network_mode: host (libere 49/tcp e 1812:1813/udp no ufw antes de atualizar); Site/Localização no cadastro de equipamento; confirmação de senha e redefinição por e-mail.",
    ],
  },
  {
    version: "1.1.1",
    date: "2026-10-19",
    changes: [
      "Correção: o backup (manual e automático) falhava com UnicodeEncodeError quando um grupo de usuário tinha faixa de IP com octeto ≥ 128 (ex.: 200.x) ou IPv6; os valores binários passam a ir no dump em hexadecimal.",
      "Backup por FTP: quando a porta de dados passiva não abre (firewall liberando só a porta 21), o erro passa a indicar a porta e o que liberar no lugar de “TimeoutError: timed out”, e o Testar conexão no modo só de gravação passa a abrir o canal de dados — antes passava mesmo com a faixa passiva bloqueada.",
    ],
  },
  {
    version: "1.1.0",
    date: "2026-10-19",
    changes: [
      "Backup automático agendado por FTP/FTPS em Backup e restauração: horário e fuso diários, cifra com a FERNET_KEY (.sql.enc) ou .sql.gz, histórico de accounting opcional, cópias mantidas no FTP, Testar conexão e Executar agora. Nenhuma cópia fica no servidor.",
      "Opção “Destino só de gravação (Pulse Backup)”: envia direto com o nome final e não apaga nada no FTP — a retenção fica no servidor de backup. O dump passa a ter cabeçalho/rodapé no formato do mysqldump, para o Pulse Backup conferir se chegou completo.",
      "Novo serviço backup-worker no docker-compose. Execuções registradas na Auditoria (backup_schedule).",
      "Restaurar backup aceita também o .sql.gz.",
      "Correção: em instalação nova o banco não subia (permissão do TACACS+ concedida antes de a tabela existir); a permissão passa a ser aplicada pela migração, inclusive em instalações antigas.",
    ],
  },
  {
    version: "1.0.0",
    date: "2026-09-25",
    changes: [
      "Versão de lançamento — painel e AAA (RADIUS + TACACS+) estáveis para uso em produção.",
      "Painel: indicadores de quantidade de equipamentos TACACS+ e RADIUS, e “Top dispositivos” (NAS mais acessado) nos últimos 7 dias, ao lado do “Top usuários”.",
      "Onda animada decorativa no login, no cabeçalho e no rodapé do painel. Menu lateral pode ser recolhido para uma faixa só com ícones (o logo diminui mas continua visível); a preferência fica salva no navegador.",
      "Rodapé (copyright e Política de Privacidade) sai da barra lateral — onde sumia com o menu recolhido — e passa a ficar sempre ao final da página, em qualquer tela.",
      "Novo fabricante ZTE ZXAN (OLTs Titan C6xx) via TACACS+.",
      "Correção: a tela Authorization volta a mostrar o IP de origem em comandos TACACS+ cujo pacote chega sem IP próprio, reaproveitando o IP do login daquela mesma sessão.",
      "Correção: a checagem de allowlist de IP de origem do grupo passa a usar o IP real do técnico, e não mais o do equipamento.",
      "Correção: priv-lvl e AV pairs do perfil de privilégio voltam a ser aplicados no login TACACS+ de qualquer serviço, não só no shell.",
      "Correção: restaurar um backup volta a regenerar o pulse.cfg do TACACS+ e não trava mais diante de uma chave ilegível.",
      "index.html passa a ir com Cache-Control: no-cache, evitando que o navegador fique preso numa versão antiga do painel depois de uma atualização.",
    ],
  },
  {
    version: "0.5.0",
    date: "2026-09-09",
    changes: [
      "2FA (TOTP) para o painel: QR code no cadastro, códigos de recuperação de uso único e “lembrar deste dispositivo” (pula o código por 30 dias, com gestão e revogação no modal de 2FA).",
      "Bloqueio de login progressivo, revelar segredo RADIUS, convite de usuário por e-mail (SMTP), troca da própria senha e backups cifrados.",
      "Papéis afinados: o operador não vê Auditoria nem Grupos de usuário e não exclui usuários/equipamentos; o auditor fica só com a leitura de equipamentos e dos relatórios AAA. Aviso para ativar o 2FA também para operador.",
      "Fabricante A10 Networks ACOS (Thunder CGN) via RADIUS e TACACS+; exceção por equipamento à exigência de Message-Authenticator (firmware antigo, BlastRADIUS).",
      "Chave TACACS+ padrão do grupo: revelar, status na lista e herança visível no equipamento; o segredo RADIUS some quando o grupo fala TACACS+.",
      "Tela Authentication com IP de origem/destino e eventos TACACS+.",
      "Painel repaginado: janela de 7 dias (era 24h), gráfico de barras de autenticações por dia e área de sessões por dia, sucessos e falhas lado a lado com IP de origem, botão Atualizar nas telas de relatórios e auditoria.",
      "Auditoria ganha a aba “Dispositivos 2FA”: dispositivos memorizados ativos + histórico de memorização/remoção.",
      "Configuração → LGPD: nome e e-mail da empresa exibidos no Aviso de Privacidade e prazos de retenção (logins/accounting, auditoria e usuários de autenticação inativos). O sistema apaga automaticamente, uma vez por dia, o que passar do prazo — 0 desliga a exclusão.",
      "Idioma da interface (pt-BR / en-US): idioma padrão no cadastro do usuário do painel (ao lado do fuso horário) e troca rápida no menu do topo. Datas seguem o idioma escolhido.",
      "Textos do painel padronizados em pt-BR.",
      "Menu vira gaveta sobreposta em telas menores; área central mais larga e sem rolagem horizontal da página. Correção: “Notas de versão” e demais modais agora abrem centralizados.",
    ],
  },
  {
    version: "0.4.0",
    date: "2026-09-04",
    changes: [
      "Servidor TACACS+ (tac_plus-ng) ao lado do RADIUS, usando os mesmos usuários, perfis e grupos via um backend MySQL (MAVIS).",
      "Cada equipamento (ou o grupo de equipamentos) escolhe falar RADIUS ou TACACS+, com chave TACACS+ própria ou herdada. MikroTik continua só RADIUS; TACACS+ cobre Huawei/Juniper/Datacom.",
      "Perfil de privilégio ganha priv-lvl (0–15) e AV pairs extra para TACACS+. Os comandos executados via TACACS+ aparecem nas telas Authorization e Accounting.",
    ],
  },
  {
    version: "0.3.0",
    date: "2026-09-03",
    changes: [
      "Relatórios divididos em Authentication (logins), Authorization (comandos executados, com IP de origem) e Accounting (abas Comandos e Sessões). Filtros por usuário / NAS / período e export CSV.",
      "Contabilização de comandos: o FreeRADIUS grava o comando quando o equipamento o envia via Accounting (Cisco/shell:cmd direto; demais fabricantes mapeiam o VSA — ver RUNBOOK).",
      "Fuso horário por usuário do painel (cadastro → Fuso horário, padrão America/Sao_Paulo). As datas do painel deixam de aparecer adiantadas.",
    ],
  },
  {
    version: "0.2.0",
    date: "2026-09-03",
    changes: [
      "Backup e restauração pelo painel (Configuração → Backup e restauração, só superadmin): baixa um .sql com esquema e dados de todas as tabelas, com opção de incluir ou não o histórico de accounting.",
      "Restauração recria o banco a partir do arquivo enviado, mediante confirmação explícita; a sessão pode cair e exigir novo login. Exportação e restauração ficam registradas na auditoria.",
      "Login administrativo em MikroTik agora funciona: suporte a MS-CHAPv2 (o RouterOS não usa PAP). Usuários criados antes desta versão precisam de um “Redefinir senha” para autenticar em MikroTik.",
      "Correção: o FreeRADIUS não recebia pacotes RADIUS externos por um problema de rede do container.",
    ],
  },
  {
    version: "0.1.0",
    date: "2026-09-02",
    changes: [
      "Lançamento inicial — AAA completo com FreeRADIUS 3.2 + MySQL 8.",
      "Authentication: PAP com senha armazenada em hash SSHA2-512.",
      "Authorization: perfis de privilégio traduzidos para atributos RADIUS de cada fabricante (Huawei, Juniper, Datacom, Mikrotik); VSAs dos demais fabricantes removidos da resposta.",
      "Accounting: sessões (radacct), eventos de autenticação (radpostauth), dashboard, filtros e exportação CSV.",
      "Cadastro de usuários de autenticação nos equipamentos, com perfil, validade e reset de senha.",
      "Grupos de usuário: allowlist de IP de origem — se o IP do request RADIUS não estiver nas faixas do grupo, a autenticação é negada.",
      "Cadastro de equipamentos (clientes RADIUS) e de grupos de equipamentos (fabricantes) com segredo RADIUS padrão herdável — trocar o segredo do grupo re-propaga aos equipamentos que o herdam.",
      "Clientes RADIUS resolvidos por SQL em tempo de request (sem reload ao cadastrar equipamento).",
      "Painel seguro: login JWT + refresh com rotação e detecção de reuso, RBAC, proteção CSRF, cabeçalhos de segurança, rate-limit no login.",
      "Usuários do painel com papéis superadmin / admin / operator / auditor e log de auditoria de todas as ações.",
      "Tema claro/escuro automático conforme o navegador; menu lateral agrupado com ícones.",
      "Aviso de Privacidade (LGPD) acessível pelo rodapé, descrevendo o tratamento de nome, e-mail e registros de acesso.",
      "Endurecimento de segurança: bloqueio de conta após tentativas de login, verificação de senha em tempo constante, CSP no HTML, /api/docs e /api/metrics fechados por padrão, senha mínima de 12 para credenciais de equipamento, rate-limit via Redis, radius_svc com privilégio mínimo, dependências atualizadas (0 vulnerabilidades).",
    ],
  },
];

export const APP_VERSION = "0.5.0";

export interface ChangelogEntry {
  version: string;
  date: string;
  changes: string[];
}

/** Mais recente primeiro. */
export const CHANGELOG: ChangelogEntry[] = [
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

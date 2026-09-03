export const APP_VERSION = "0.2.0";

export interface ChangelogEntry {
  version: string;
  date: string;
  changes: string[];
}

/** Mais recente primeiro. */
export const CHANGELOG: ChangelogEntry[] = [
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
      "Utilizadores do sistema com papéis superadmin / admin / operator / auditor e log de auditoria de todas as ações.",
      "Tema claro/escuro automático conforme o navegador; menu lateral agrupado com ícones.",
      "Aviso de Privacidade (LGPD) acessível pelo rodapé, descrevendo o tratamento de nome, e-mail e registros de acesso.",
      "Endurecimento de segurança: bloqueio de conta após tentativas de login, verificação de senha em tempo constante, CSP no HTML, /api/docs e /api/metrics fechados por padrão, senha mínima de 12 para credenciais de equipamento, rate-limit via Redis, radius_svc com privilégio mínimo, dependências atualizadas (0 vulnerabilidades).",
    ],
  },
];

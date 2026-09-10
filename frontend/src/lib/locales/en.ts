/**
 * en-US translations. Keys are the pt-BR source strings; a missing key falls
 * back to the key itself (pt-BR). Keep entries alphabetical-ish by area.
 */
export const en: Record<string, string> = {
  // ---- Navegação / menu lateral ----
  Painel: "Dashboard",
  Equipamentos: "Devices",
  "Grupo de equipamentos": "Device group",
  Usuários: "Users",
  "Usuários de autenticação": "Authentication users",
  "Grupos de usuário": "User groups",
  "Perfis de privilégio": "Privilege profiles",
  Relatórios: "Reports",
  Autenticação: "Authentication",
  Autorização: "Authorization",
  "Contabilização (Accounting)": "Accounting",
  Auditoria: "Audit",
  Configuração: "Settings",
  "Usuários do painel": "Panel users",
  "Servidor SMTP": "SMTP server",
  "Backup e restauração": "Backup & restore",

  // ---- Cabeçalho / menu do usuário ----
  Sair: "Log out",
  "Abrir menu": "Open menu",
  "Fechar menu": "Close menu",
  "Alterar senha": "Change password",
  "Ativar 2FA": "Enable 2FA",
  "2FA (ativo)": "2FA (on)",
  Idioma: "Language",
  "Sua conta tem privilégios de {role} e ainda não tem 2FA ativo.":
    "Your account has {role} privileges and 2FA is not enabled yet.",
  "Ativar agora": "Enable now",
  "Idioma da interface atualizado": "Interface language updated",

  // ---- Botões / ações comuns ----
  Salvar: "Save",
  Cancelar: "Cancel",
  Fechar: "Close",
  Editar: "Edit",
  Excluir: "Delete",
  Remover: "Remove",
  Detalhes: "Details",
  Copiar: "Copy",
  "Baixar .txt": "Download .txt",
  Atualizar: "Refresh",
  "Recarregar os dados desta tela": "Reload this screen's data",
  Verificar: "Verify",
  Voltar: "Back",
  "Exportar CSV": "Export CSV",
  Anterior: "Previous",
  Próxima: "Next",
  Entrar: "Sign in",

  // ---- Toasts genéricos ----
  "Erro ao salvar": "Failed to save",
  "Erro ao remover": "Failed to remove",
  Erro: "Error",
  "Equipamento salvo": "Device saved",
  "Equipamento removido": "Device removed",
  "Usuário salvo": "User saved",
  "Usuário removido": "User removed",
  "Grupo salvo": "Group saved",
  "Grupo removido": "Group removed",
  "Fabricante salvo": "Vendor saved",
  "Fabricante removido": "Vendor removed",
  "Perfil removido": "Profile removed",
  Copiado: "Copied",
  "Não foi possível copiar": "Could not copy",
  "Códigos copiados": "Codes copied",

  // ---- Login / definir senha ----
  Usuário: "Username",
  Senha: "Password",
  "Falha ao entrar": "Sign-in failed",
  "Código inválido": "Invalid code",
  "Código de recuperação": "Recovery code",
  "Código de verificação": "Verification code",
  "Digite o código de 6 dígitos do seu aplicativo autenticador.":
    "Enter the 6-digit code from your authenticator app.",
  "Digite um dos seus códigos de recuperação (uso único).":
    "Enter one of your recovery codes (single use).",
  "Usar o código do autenticador": "Use the authenticator code",
  "Usar um código de recuperação": "Use a recovery code",
  "Confiar neste dispositivo (não pedir o código por 30 dias)":
    "Trust this device (don't ask for the code for 30 days)",
  "Nova senha": "New password",
  "Confirmar senha": "Confirm password",
  "Confirmar nova senha": "Confirm new password",
  "Senha atual": "Current password",
  "Mínimo 10 caracteres.": "At least 10 characters.",
  "As senhas não coincidem": "Passwords don't match",
  "Senha alterada": "Password changed",
  "Erro ao alterar a senha": "Failed to change password",
  "Link inválido: token ausente.": "Invalid link: missing token.",
  "Convite inválido ou expirado": "Invalid or expired invitation",
  "Falha ao definir a senha": "Failed to set password",
  "Criar senha e entrar": "Set password and sign in",
  "Olá, {nome}. Defina a senha da sua conta ({login}) para concluir o cadastro.":
    "Hello, {nome}. Set your account password ({login}) to finish signing up.",

  // ---- 2FA ----
  "Autenticação em duas etapas (2FA)": "Two-factor authentication (2FA)",
  "O 2FA está ativo na sua conta.": "2FA is active on your account.",
  "O 2FA está desativado. Ative para exigir um código do seu aplicativo autenticador (Google Authenticator, Authy, 1Password…) a cada login.":
    "2FA is disabled. Enable it to require a code from your authenticator app (Google Authenticator, Authy, 1Password…) on every sign-in.",
  "Códigos de recuperação restantes:": "Recovery codes left:",
  "Gerar novos": "Generate new",
  "Você está quase sem códigos — gere um lote novo e guarde-o.":
    "You're almost out of codes — generate a new batch and store it.",
  "Desativar 2FA": "Disable 2FA",
  "Confirmar e ativar": "Confirm and enable",
  "Código gerado pelo app": "Code from the app",
  "Já guardei os códigos": "I saved the codes",
  "Gerar novos códigos": "Generate new codes",
  "Código do autenticador ou de recuperação": "Authenticator or recovery code",
  "2FA ativado": "2FA enabled",
  "2FA desativado": "2FA disabled",
  "Novos códigos gerados": "New codes generated",
  "Dispositivos confiáveis": "Trusted devices",
  "Esquecer todos": "Forget all",
  "Navegadores que pulam o código do 2FA no login. A validade (30 dias) renova a cada acesso.":
    "Browsers that skip the 2FA code at sign-in. The 30-day window renews on each use.",
  "Nenhum — o 2FA é pedido em todo login.": "None — 2FA is asked on every sign-in.",
  "(este dispositivo)": "(this device)",
  "Todos os dispositivos foram esquecidos": "All devices were forgotten",
  "Dispositivo removido": "Device removed",
  Carregando: "Loading",
  "Guarde estes códigos de recuperação num lugar seguro. Cada um funciona uma única vez e serve para entrar ou desativar o 2FA se você perder o aplicativo autenticador.":
    "Keep these recovery codes somewhere safe. Each one works once and lets you sign in or disable 2FA if you lose your authenticator app.",
  "Erro ao iniciar o 2FA": "Failed to start 2FA",
  "IP desconhecido": "unknown IP",
  "expira {data}": "expires {data}",
  "Confirme sua senha e um código atual (do autenticador ou um código de recuperação ainda válido). Os códigos anteriores deixam de funcionar.":
    "Confirm your password and a current code (from the authenticator or a still-valid recovery code). Previous codes stop working.",
  "Confirme sua senha e um código para desativar o 2FA — pode ser o código atual do autenticador ou um dos seus códigos de recuperação.":
    "Confirm your password and a code to disable 2FA — the current authenticator code or one of your recovery codes.",
  'No seu aplicativo autenticador, escaneie o QR code abaixo — ou adicione a conta manualmente com esta chave ("chave baseada em tempo"):':
    'In your authenticator app, scan the QR code below — or add the account manually with this key ("time-based key"):',
  "Alguns apps aceitam colar o link diretamente:": "Some apps accept pasting the link directly:",
  "QR code para configurar o 2FA no aplicativo autenticador":
    "QR code to set up 2FA in your authenticator app",

  // ---- Títulos / subtítulos das páginas ----
  "Visão geral do AAA — últimos 7 dias": "AAA overview — last 7 days",
  "Clientes RADIUS (NAS)": "RADIUS clients (NAS)",
  "Fabricante / grupo: define a tradução de VSA e o segredo RADIUS padrão herdado pelos equipamentos":
    "Vendor / group: sets the VSA translation and the default RADIUS secret inherited by devices",
  "Contas que autenticam nos equipamentos via RADIUS":
    "Accounts that authenticate on devices via RADIUS",
  "Restringem a autenticação por IP de origem: fora das faixas do grupo, o RADIUS rejeita":
    "Restrict authentication by source IP: outside the group's ranges, RADIUS rejects",
  "Mapeiam um perfil abstrato para atributos RADIUS de cada fabricante (radgroupreply)":
    "Map an abstract profile to per-vendor RADIUS attributes (radgroupreply)",
  "Tentativas de login nos equipamentos (RADIUS e TACACS+), com IP de origem e destino":
    "Login attempts on devices (RADIUS and TACACS+), with source and destination IP",
  "Comandos executados nos equipamentos, com o IP de origem de quem executou":
    "Commands run on devices, with the source IP of who ran them",
  "Comandos executados nos equipamentos e sessões de login (radacct)":
    "Commands run on devices and login sessions (radacct)",
  "Todas as ações administrativas realizadas no painel":
    "All administrative actions performed in the panel",
  "Dispositivos memorizados no 2FA (ativos) e o histórico de memorização/remoção":
    "Devices remembered for 2FA (active) and the trust/removal history",
  "Contas de acesso a este painel (não confundir com usuários de autenticação)":
    "Accounts that sign in to this panel (not to be confused with authentication users)",
  "Usado para enviar o convite de registro (criação de senha) aos usuários do painel":
    "Used to send the sign-up invitation (password creation) to panel users",
  "Cópia completa do banco (RADIUS + painel) para recuperação em caso de falha":
    "Full database copy (RADIUS + panel) for disaster recovery",
  "Identificação do controlador exibida no Aviso de Privacidade e prazos de retenção de dados":
    "Data controller identification shown in the Privacy Notice and data retention periods",

  // ---- Dashboard ----
  "Sessões ativas": "Active sessions",
  "Sessões (7d)": "Sessions (7d)",
  "Logins aceitos (7d)": "Accepted logins (7d)",
  "Logins negados (7d)": "Rejected logins (7d)",
  "Top usuários · 7 dias": "Top users · 7 days",
  "Sem sessões nos últimos 7 dias": "No sessions in the last 7 days",
  "Falhas de autenticação recentes": "Recent authentication failures",
  "Sucessos de autenticação recentes": "Recent authentication successes",
  "Nenhuma falha recente": "No recent failures",
  "Nenhum sucesso recente": "No recent successes",
  "Autenticações por dia · 7 dias": "Authentications per day · 7 days",
  "Sessões por dia · 7 dias": "Sessions per day · 7 days",
  "Aceitos vs. negados (7 dias)": "Accepted vs. rejected (7 days)",
  "{n}% de aprovação": "{n}% approval",
  "{n}% aprov.": "{n}% appr.",
  "{total} no total · pico {pico}": "{total} total · peak {pico}",
  "sem eventos": "no events",
  "sem eventos nos últimos 7 dias": "no events in the last 7 days",
  "sem sessões": "no sessions",
  sessões: "sessions",
  "Distribuição por usuário": "Distribution by user",
  "Sem dados": "No data",
  Aceitos: "Accepted",
  Negados: "Rejected",

  // ---- Botões "Novo ..." ----
  "Novo equipamento": "New device",
  "Novo usuário": "New user",
  "Novo grupo": "New group",
  "Novo perfil": "New profile",
  "Novo fabricante": "New vendor",

  // ---- Estados vazios comuns ----
  "Nenhum registro.": "No records.",
  "Nenhum equipamento neste grupo.": "No devices in this group.",
  "Nenhum evento para o filtro.": "No events for this filter.",
  "Nenhum usuário encontrado.": "No users found.",

  // ---- Tabela / paginação ----
  "{n} registro": "{n} record",
  "{n} registros": "{n} records",

  // ---- Filtros de relatório / colunas comuns ----
  "IP do NAS": "NAS IP",
  De: "From",
  Até: "To",
  Data: "Date",
  Resultado: "Result",
  Protocolo: "Protocol",
  Origem: "Source",
  Destino: "Destination",
  Ação: "Action",
  Evento: "Event",
  Dispositivo: "Device",
  Autor: "Actor",
  Entidade: "Entity",
  Comando: "Command",
  NAS: "NAS",
  Nome: "Name",
  Papel: "Role",
  Estado: "Status",
  Site: "Site",
  Atualizado: "Updated",
  "Último login": "Last login",
  "Buscar…": "Search…",
  "Buscar por nome, IP, site…": "Search by name, IP, site…",
  "Buscar por login, nome ou e-mail…": "Search by login, name or email…",

  // ---- Aviso de Privacidade (/privacidade) ----
  "Aviso de Privacidade": "Privacy Notice",
  "Pulse RADIUS · última atualização em {data}": "Pulse RADIUS · last updated {data}",
  "← Voltar": "← Back",
  "1. Sobre este aviso": "1. About this notice",
  "O Pulse RADIUS é um sistema interno de controle de acesso (AAA — autenticação, autorização e contabilização) a equipamentos de rede. Este aviso descreve quais dados pessoais são tratados, com que finalidade e quais são os seus direitos, nos termos da Lei nº 13.709/2018 (Lei Geral de Proteção de Dados — LGPD).":
    "Pulse RADIUS is an internal access-control system (AAA — authentication, authorization and accounting) for network devices. This notice describes which personal data is processed, for what purpose, and what your rights are, under Brazilian Law 13.709/2018 (LGPD).",
  "2. Controlador e Encarregado (DPO)": "2. Controller and Data Protection Officer (DPO)",
  "Controlador:": "Controller:",
  "Pedidos relativos a dados pessoais devem ser enviados ao Encarregado pelo Tratamento de Dados Pessoais:":
    "Requests regarding personal data should be sent to the Data Protection Officer:",
  "3. Dados pessoais tratados": "3. Personal data processed",
  "Usuários do painel:": "Panel users:",
  "nome, e-mail, nome de usuário (login), papel/função, data e hora do último acesso e a senha — armazenada apenas como hash Argon2id, nunca em texto claro.":
    "name, email, username (login), role, date and time of last access, and the password — stored only as an Argon2id hash, never in clear text.",
  "Usuários de autenticação nos equipamentos:": "Device authentication users:",
  "nome e e-mail (opcionais), nome de usuário e a senha — armazenada como hash SSHA2-512.":
    "name and email (optional), username, and the password — stored as an SSHA2-512 hash.",
  "Registros de autenticação e sessão (accounting):": "Authentication and session records (accounting):",
  "nome de usuário, endereço IP de origem, identificador da estação (ex.: IP/porta), data e hora de início e término, resultado (aceito/negado) e causa de término.":
    "username, source IP address, station identifier (e.g. IP/port), start and end date/time, result (accepted/rejected) and termination cause.",
  "Registros de auditoria:": "Audit records:",
  "autor da ação, endereço IP, identificação do navegador (user-agent) e o conteúdo alterado (que pode conter nome e e-mail).":
    "the actor, IP address, browser identification (user-agent) and the changed content (which may contain name and email).",
  "Cookies:": "Cookies:",
  "estritamente necessários para manter a sessão autenticada no painel (tokens de acesso, de renovação e de proteção CSRF). Não há cookies de rastreamento, publicidade ou analítica.":
    "strictly necessary to keep the panel session authenticated (access, refresh and CSRF-protection tokens). There are no tracking, advertising or analytics cookies.",
  "4. Finalidades do tratamento": "4. Purposes of processing",
  "Autenticar e autorizar o acesso administrativo a equipamentos de rede (Huawei, Juniper, Datacom, Mikrotik e outros).":
    "Authenticate and authorize administrative access to network devices (Huawei, Juniper, Datacom, Mikrotik and others).",
  "Registrar e auditar sessões e ações administrativas, para segurança, rastreabilidade e diagnóstico de incidentes.":
    "Record and audit sessions and administrative actions for security, traceability and incident diagnosis.",
  "Gerenciar as contas de usuários do próprio painel.": "Manage the panel's own user accounts.",
  "5. Base legal": "5. Legal basis",
  "O tratamento apoia-se no cumprimento de obrigação legal ou regulatória, na execução de contrato (inclusive de trabalho ou de prestação de serviços) e no legítimo interesse do controlador em manter a segurança e a integridade da sua infraestrutura de rede (art. 7º, incisos II, V e IX, da LGPD).":
    "Processing relies on compliance with a legal or regulatory obligation, on the performance of a contract (including employment or service contracts) and on the controller's legitimate interest in maintaining the security and integrity of its network infrastructure (art. 7, items II, V and IX of the LGPD).",
  "6. Compartilhamento": "6. Sharing",
  "Os dados são tratados exclusivamente na infraestrutura do controlador e não são vendidos nem compartilhados com terceiros, ressalvado o cumprimento de obrigação legal ou de ordem de autoridade competente.":
    "Data is processed exclusively on the controller's infrastructure and is neither sold nor shared with third parties, except to comply with a legal obligation or an order from a competent authority.",
  "7. Retenção": "7. Retention",
  "Registros de accounting (logins, comandos, sessões):": "Accounting records (logins, commands, sessions):",
  "Registros de auditoria do painel:": "Panel audit records:",
  "Contas de usuários de autenticação desativadas: excluídas após {prazo} sem uso.":
    "Disabled device authentication accounts: deleted after {prazo} unused.",
  "Dados de conta são mantidos enquanto a conta existir; após a exclusão, permanecem apenas as referências mínimas necessárias nos registros de auditoria.":
    "Account data is kept while the account exists; after deletion, only the minimum references needed remain in the audit records.",
  "8. Segurança da informação": "8. Information security",
  "Senhas armazenadas em hash (Argon2id para o painel, SSHA2-512 para os usuários RADIUS); segredos compartilhados (shared secrets) cifrados em repouso; comunicação via HTTPS; controle de acesso por papéis (RBAC); proteção contra CSRF; e limitação de tentativas de login.":
    "Passwords stored hashed (Argon2id for the panel, SSHA2-512 for RADIUS users); shared secrets encrypted at rest; HTTPS communication; role-based access control (RBAC); CSRF protection; and login rate limiting.",
  "9. Direitos do titular": "9. Data subject rights",
  "Você pode solicitar confirmação da existência de tratamento, acesso, correção, anonimização, portabilidade, eliminação e informação sobre compartilhamento, além de revogar consentimento quando aplicável. Encaminhe o pedido para":
    "You may request confirmation that processing exists, access, correction, anonymization, portability, deletion and information about sharing, as well as withdraw consent where applicable. Send your request to",
  "10. Alterações deste aviso": "10. Changes to this notice",
  "Este aviso pode ser atualizado a qualquer momento; a data no topo indica a última revisão.":
    "This notice may be updated at any time; the date at the top shows the last revision.",
  "mantidos enquanto forem necessários": "kept as long as necessary",
  "{days} dias (aprox. {months} meses)": "{days} days (approx. {months} months)",

  "Política de Privacidade": "Privacy Policy",

  // ---- Notas de versão (changelog) — versão atual ----
  "Notas de versão": "Release notes",
  "2FA (TOTP) para o painel: QR code no cadastro, códigos de recuperação de uso único e “lembrar deste dispositivo” (pula o código por 30 dias, com gestão e revogação no modal de 2FA).":
    "Panel 2FA (TOTP): QR code on setup, single-use recovery codes and “trust this device” (skips the code for 30 days, managed and revocable in the 2FA dialog).",
  "Bloqueio de login progressivo, revelar segredo RADIUS, convite de usuário por e-mail (SMTP), troca da própria senha e backups cifrados.":
    "Progressive login lockout, RADIUS secret reveal, user invitation by email (SMTP), self-service password change and encrypted backups.",
  "Papéis afinados: o operador não vê Auditoria nem Grupos de usuário e não exclui usuários/equipamentos; o auditor fica só com a leitura de equipamentos e dos relatórios AAA. Aviso para ativar o 2FA também para operador.":
    "Refined roles: operators no longer see Audit or User groups and cannot delete users/devices; auditors are limited to reading devices and the AAA reports. The “enable 2FA” notice now also shows for operators.",
  "Fabricante A10 Networks ACOS (Thunder CGN) via RADIUS e TACACS+; exceção por equipamento à exigência de Message-Authenticator (firmware antigo, BlastRADIUS).":
    "A10 Networks ACOS (Thunder CGN) vendor over RADIUS and TACACS+; per-device exception to the Message-Authenticator requirement (old firmware, BlastRADIUS).",
  "Chave TACACS+ padrão do grupo: revelar, status na lista e herança visível no equipamento; o segredo RADIUS some quando o grupo fala TACACS+.":
    "Group default TACACS+ key: reveal, status in the list and inheritance shown on the device; the RADIUS secret is hidden when the group speaks TACACS+.",
  "Tela Authentication com IP de origem/destino e eventos TACACS+.":
    "Authentication screen with source/destination IP and TACACS+ events.",
  "Painel repaginado: janela de 7 dias (era 24h), gráfico de barras de autenticações por dia e área de sessões por dia, sucessos e falhas lado a lado com IP de origem, botão Atualizar nas telas de relatórios e auditoria.":
    "Redesigned dashboard: 7-day window (was 24h), bar chart of authentications per day and area chart of sessions per day, successes and failures side by side with source IP, Refresh button on the report and audit screens.",
  "Auditoria ganha a aba “Dispositivos 2FA”: dispositivos memorizados ativos + histórico de memorização/remoção.":
    "Audit gains the “2FA devices” tab: active remembered devices + trust/removal history.",
  "Configuração → LGPD: nome e e-mail da empresa exibidos no Aviso de Privacidade e prazos de retenção (logins/accounting, auditoria e usuários de autenticação inativos). O sistema apaga automaticamente, uma vez por dia, o que passar do prazo — 0 desliga a exclusão.":
    "Settings → LGPD: company name and email shown in the Privacy Notice and retention periods (logins/accounting, audit and inactive authentication users). The system deletes whatever is past the period automatically, once a day — 0 disables deletion.",
  "Idioma da interface (pt-BR / en-US): idioma padrão no cadastro do usuário do painel (ao lado do fuso horário) e troca rápida no menu do topo. Datas seguem o idioma escolhido.":
    "Interface language (pt-BR / en-US): default language on the panel user form (next to the timezone) and a quick switch in the top menu. Dates follow the chosen language.",
  "Textos do painel padronizados em pt-BR.": "Panel wording standardized to pt-BR.",
  "Menu vira gaveta sobreposta em telas menores; área central mais larga e sem rolagem horizontal da página. Correção: “Notas de versão” e demais modais agora abrem centralizados.":
    "The menu becomes an overlay drawer on smaller screens; wider main area and no horizontal page scroll. Fix: “Release notes” and other dialogs now open centered.",
  "Memorizado": "Remembered",
  "Último uso": "Last used",
  Expira: "Expires",
  "Início": "Start",
  Fim: "End",
  "Duração": "Duration",
  Causa: "Cause",
};

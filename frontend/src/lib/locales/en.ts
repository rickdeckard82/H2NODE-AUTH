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
  "sem eventos": "no events",
  "sem eventos nos últimos 7 dias": "no events in the last 7 days",
  "sem sessões": "no sessions",
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
};

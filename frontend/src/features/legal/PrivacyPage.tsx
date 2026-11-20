import { useQuery } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Logo } from "../../components/Logo";
import { api } from "../../lib/api";
import { useT } from "../../lib/i18n";
import { LEGAL } from "../../lib/legal";

interface LegalNotice {
  org_name: string;
  dpo_email: string;
  accounting_retention_days: number;
  audit_retention_days: number;
  auth_user_retention_days: number;
  updated_at: string | null;
}

type T = (key: string, vars?: Record<string, string | number>) => string;

/** "365 days (approx. 12 months)" ou, com 0, "kept as long as necessary". */
function retLabel(days: number, t: T): string {
  if (!days || days <= 0) return t("mantidos enquanto forem necessários");
  const months = Math.round((days / 30) * 10) / 10;
  return t("{days} dias (aprox. {months} meses)", { days, months });
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="space-y-2">
      <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
      <div className="space-y-2 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
        {children}
      </div>
    </section>
  );
}

export default function PrivacyPage() {
  const t = useT();
  const { data } = useQuery({
    queryKey: ["legal-notice"],
    queryFn: () => api.get<LegalNotice>("/settings/legal"),
    retry: false,
  });

  const orgName = data?.org_name || LEGAL.orgName;
  const dpoEmail = data?.dpo_email || LEGAL.dpoEmail;
  const lastUpdated = data?.updated_at
    ? new Date(data.updated_at).toLocaleDateString("pt-BR")
    : LEGAL.lastUpdated;
  const accountingRetention = data
    ? retLabel(data.accounting_retention_days, t)
    : LEGAL.accountingRetention;
  const auditRetention = data ? retLabel(data.audit_retention_days, t) : LEGAL.auditRetention;
  const userRetention =
    data && data.auth_user_retention_days > 0 ? retLabel(data.auth_user_retention_days, t) : null;

  return (
    <div className="min-h-screen bg-slate-100 dark:bg-slate-950">
      <div className="mx-auto max-w-2xl px-4 py-10">
        <div className="mb-6 flex items-center gap-3">
          <Logo className="h-10 w-10 shrink-0" />
          <div>
            <h1 className="text-xl font-bold">{t("Aviso de Privacidade")}</h1>
            <p className="text-xs text-slate-400 dark:text-slate-500">
              {t("H2NODE Auth · última atualização em {data}", { data: lastUpdated })}
            </p>
          </div>
        </div>

        <div className="card space-y-6 p-6">
          <Section title={t("1. Sobre este aviso")}>
            <p>
              {t(
                "O H2NODE Auth é um sistema interno de controle de acesso (AAA — autenticação, autorização e contabilização) a equipamentos de rede. Este aviso descreve quais dados pessoais são tratados, com que finalidade e quais são os seus direitos, nos termos da Lei nº 13.709/2018 (Lei Geral de Proteção de Dados — LGPD).",
              )}
            </p>
          </Section>

          <Section title={t("2. Controlador e Encarregado (DPO)")}>
            <p>
              {t("Controlador:")} <strong>{orgName}</strong>.{" "}
              {t(
                "Pedidos relativos a dados pessoais devem ser enviados ao Encarregado pelo Tratamento de Dados Pessoais:",
              )}{" "}
              <a
                className="text-brand-600 hover:underline dark:text-brand-400"
                href={`mailto:${dpoEmail}`}
              >
                {dpoEmail}
              </a>
              .
            </p>
          </Section>

          <Section title={t("3. Dados pessoais tratados")}>
            <ul className="list-disc space-y-1.5 pl-5">
              <li>
                <strong>{t("Usuários do painel:")}</strong>{" "}
                {t(
                  "nome, e-mail, nome de usuário (login), papel/função, data e hora do último acesso e a senha — armazenada apenas como hash Argon2id, nunca em texto claro.",
                )}
              </li>
              <li>
                <strong>{t("Usuários de autenticação nos equipamentos:")}</strong>{" "}
                {t(
                  "nome e e-mail (opcionais), nome de usuário e a senha — armazenada como hash SSHA2-512.",
                )}
              </li>
              <li>
                <strong>{t("Registros de autenticação e sessão (accounting):")}</strong>{" "}
                {t(
                  "nome de usuário, endereço IP de origem, identificador da estação (ex.: IP/porta), data e hora de início e término, resultado (aceito/negado) e causa de término.",
                )}
              </li>
              <li>
                <strong>{t("Registros de auditoria:")}</strong>{" "}
                {t(
                  "autor da ação, endereço IP, identificação do navegador (user-agent) e o conteúdo alterado (que pode conter nome e e-mail).",
                )}
              </li>
              <li>
                <strong>{t("Cookies:")}</strong>{" "}
                {t(
                  "estritamente necessários para manter a sessão autenticada no painel (tokens de acesso, de renovação e de proteção CSRF). Não há cookies de rastreamento, publicidade ou analítica.",
                )}
              </li>
            </ul>
          </Section>

          <Section title={t("4. Finalidades do tratamento")}>
            <ul className="list-disc space-y-1.5 pl-5">
              <li>
                {t(
                  "Autenticar e autorizar o acesso administrativo a equipamentos de rede (Huawei, Juniper, Datacom, Mikrotik e outros).",
                )}
              </li>
              <li>
                {t(
                  "Registrar e auditar sessões e ações administrativas, para segurança, rastreabilidade e diagnóstico de incidentes.",
                )}
              </li>
              <li>{t("Gerenciar as contas de usuários do próprio painel.")}</li>
            </ul>
          </Section>

          <Section title={t("5. Base legal")}>
            <p>
              {t(
                "O tratamento apoia-se no cumprimento de obrigação legal ou regulatória, na execução de contrato (inclusive de trabalho ou de prestação de serviços) e no legítimo interesse do controlador em manter a segurança e a integridade da sua infraestrutura de rede (art. 7º, incisos II, V e IX, da LGPD).",
              )}
            </p>
          </Section>

          <Section title={t("6. Compartilhamento")}>
            <p>
              {t(
                "Os dados são tratados exclusivamente na infraestrutura do controlador e não são vendidos nem compartilhados com terceiros, ressalvado o cumprimento de obrigação legal ou de ordem de autoridade competente.",
              )}
            </p>
          </Section>

          <Section title={t("7. Retenção")}>
            <ul className="list-disc space-y-1.5 pl-5">
              <li>
                {t("Registros de accounting (logins, comandos, sessões):")}{" "}
                {accountingRetention}.
              </li>
              <li>
                {t("Registros de auditoria do painel:")} {auditRetention}.
              </li>
              {userRetention && (
                <li>
                  {t(
                    "Contas de usuários de autenticação desativadas: excluídas após {prazo} sem uso.",
                    { prazo: userRetention },
                  )}
                </li>
              )}
              <li>
                {t(
                  "Dados de conta são mantidos enquanto a conta existir; após a exclusão, permanecem apenas as referências mínimas necessárias nos registros de auditoria.",
                )}
              </li>
            </ul>
          </Section>

          <Section title={t("8. Segurança da informação")}>
            <p>
              {t(
                "Senhas armazenadas em hash (Argon2id para o painel, SSHA2-512 para os usuários RADIUS); segredos compartilhados (shared secrets) cifrados em repouso; comunicação via HTTPS; controle de acesso por papéis (RBAC); proteção contra CSRF; e limitação de tentativas de login.",
              )}
            </p>
          </Section>

          <Section title={t("9. Direitos do titular")}>
            <p>
              {t(
                "Você pode solicitar confirmação da existência de tratamento, acesso, correção, anonimização, portabilidade, eliminação e informação sobre compartilhamento, além de revogar consentimento quando aplicável. Encaminhe o pedido para",
              )}{" "}
              <a
                className="text-brand-600 hover:underline dark:text-brand-400"
                href={`mailto:${dpoEmail}`}
              >
                {dpoEmail}
              </a>
              .
            </p>
          </Section>

          <Section title={t("10. Alterações deste aviso")}>
            <p>
              {t(
                "Este aviso pode ser atualizado a qualquer momento; a data no topo indica a última revisão.",
              )}
            </p>
          </Section>
        </div>

        <div className="mt-6 text-sm">
          <Link to="/" className="text-brand-600 hover:underline dark:text-brand-400">
            {t("← Voltar")}
          </Link>
        </div>
      </div>
    </div>
  );
}

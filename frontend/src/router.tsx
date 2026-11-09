import { lazy, Suspense, type ReactNode } from "react";
import { createBrowserRouter, Navigate, Outlet } from "react-router-dom";
import { Spinner, ToastProvider } from "./components/ui";
import { AppShell } from "./layouts/AppShell";
import { useAuth, type Role } from "./lib/auth";

const LoginPage = lazy(() => import("./features/auth/LoginPage"));
const SetPasswordPage = lazy(() => import("./features/auth/SetPasswordPage"));
const PrivacyPage = lazy(() => import("./features/legal/PrivacyPage"));
const DashboardPage = lazy(() => import("./features/dashboard/DashboardPage"));
const AuthUsersPage = lazy(() => import("./features/auth-users/AuthUsersPage"));
const UserGroupsPage = lazy(() => import("./features/user-groups/UserGroupsPage"));
const EquipmentPage = lazy(() => import("./features/equipment/EquipmentPage"));
const SitesPage = lazy(() => import("./features/sites/SitesPage"));
const ManufacturersPage = lazy(() => import("./features/manufacturers/ManufacturersPage"));
const PrivilegeProfilesPage = lazy(() => import("./features/privilege-profiles/PrivilegeProfilesPage"));
const SystemUsersPage = lazy(() => import("./features/system-users/SystemUsersPage"));
const BackupPage = lazy(() => import("./features/backup/BackupPage"));
const SmtpSettingsPage = lazy(() => import("./features/settings/SmtpSettingsPage"));
const LgpdSettingsPage = lazy(() => import("./features/settings/LgpdSettingsPage"));
const AccountingPage = lazy(() => import("./features/accounting/AccountingPage"));
const AuthenticationPage = lazy(() => import("./features/reports/AuthenticationPage"));
const AuthorizationPage = lazy(() => import("./features/reports/AuthorizationPage"));
const AuditPage = lazy(() => import("./features/audit/AuditPage"));

function Loader() {
  return (
    <div className="flex h-screen items-center justify-center text-brand-600">
      <Spinner className="h-8 w-8" />
    </div>
  );
}

function Protected({ roles, children }: { roles?: Role[]; children: ReactNode }) {
  const { user, loading, can } = useAuth();
  if (loading) return <Loader />;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !can(...roles)) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function Shell() {
  return (
    <ToastProvider>
      <Protected>
        <AppShell>
          <Suspense fallback={<Loader />}>
            <Outlet />
          </Suspense>
        </AppShell>
      </Protected>
    </ToastProvider>
  );
}

export const router = createBrowserRouter([
  {
    path: "/login",
    element: (
      <Suspense fallback={<Loader />}>
        <LoginPage />
      </Suspense>
    ),
  },
  {
    path: "/privacidade",
    element: (
      <Suspense fallback={<Loader />}>
        <PrivacyPage />
      </Suspense>
    ),
  },
  {
    path: "/set-password",
    element: (
      <Suspense fallback={<Loader />}>
        <SetPasswordPage />
      </Suspense>
    ),
  },
  {
    path: "/",
    element: <Shell />,
    children: [
      { index: true, element: <DashboardPage /> },
      {
        path: "auth-users",
        element: (
          <Protected roles={["operator"]}>
            <AuthUsersPage />
          </Protected>
        ),
      },
      {
        path: "user-groups",
        element: (
          <Protected roles={["admin"]}>
            <UserGroupsPage />
          </Protected>
        ),
      },
      { path: "equipment", element: <EquipmentPage /> },
      {
        path: "sites",
        element: (
          <Protected roles={["operator"]}>
            <SitesPage />
          </Protected>
        ),
      },
      {
        path: "manufacturers",
        element: (
          <Protected roles={["admin"]}>
            <ManufacturersPage />
          </Protected>
        ),
      },
      {
        path: "profiles",
        element: (
          <Protected roles={["admin"]}>
            <PrivilegeProfilesPage />
          </Protected>
        ),
      },
      { path: "auth-log", element: <AuthenticationPage /> },
      { path: "authz-log", element: <AuthorizationPage /> },
      { path: "accounting", element: <AccountingPage /> },
      {
        path: "audit",
        element: (
          <Protected roles={["admin"]}>
            <AuditPage />
          </Protected>
        ),
      },
      {
        path: "system-users",
        element: (
          <Protected roles={["superadmin"]}>
            <SystemUsersPage />
          </Protected>
        ),
      },
      {
        path: "backup",
        element: (
          <Protected roles={["superadmin"]}>
            <BackupPage />
          </Protected>
        ),
      },
      {
        path: "settings/smtp",
        element: (
          <Protected roles={["superadmin"]}>
            <SmtpSettingsPage />
          </Protected>
        ),
      },
      {
        path: "settings/lgpd",
        element: (
          <Protected roles={["superadmin"]}>
            <LgpdSettingsPage />
          </Protected>
        ),
      },
      { path: "*", element: <Navigate to="/" replace /> },
    ],
  },
]);

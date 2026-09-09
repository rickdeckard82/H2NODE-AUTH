export type VendorKind = "huawei" | "juniper" | "datacom" | "mikrotik" | "a10" | "generic";

export type AaaProtocol = "radius" | "tacacs";

export const VENDOR_KINDS: VendorKind[] = [
  "huawei",
  "juniper",
  "datacom",
  "mikrotik",
  "a10",
  "generic",
];

export interface Manufacturer {
  id: number;
  name: string;
  display_name: string;
  vendor_kind: VendorKind;
  radius_vendor_id: number | null;
  aaa_protocol: AaaProtocol;
  has_secret: boolean;
  has_tacacs_key: boolean;
  equipment_count: number;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProfileAttr {
  id?: number;
  manufacturer_id: number;
  attribute: string;
  op: string;
  value: string;
}

export interface PrivilegeProfile {
  id: number;
  name: string;
  description: string | null;
  is_builtin: boolean;
  group_name: string;
  attrs: ProfileAttr[];
  tacacs_priv_level: number;
  tacacs_extra_avpairs: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuthUser {
  id: number;
  username: string;
  full_name: string | null;
  email: string | null;
  privilege_profile_id: number;
  profile_name: string;
  auth_group_id: number | null;
  auth_group_name: string | null;
  is_active: boolean;
  expires_at: string | null;
  last_auth_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuthGroupCidr {
  id?: number;
  cidr: string;
  family?: number;
  note: string | null;
}

export interface AuthGroup {
  id: number;
  name: string;
  description: string | null;
  cidrs: AuthGroupCidr[];
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface Equipment {
  id: number;
  name: string;
  mgmt_ip: string;
  manufacturer_id: number;
  manufacturer_name: string;
  manufacturer_display: string;
  vendor_kind: VendorKind;
  model: string | null;
  site: string | null;
  shortname: string;
  coa_port: number;
  status: "active" | "maintenance" | "disabled";
  description: string | null;
  aaa_protocol: AaaProtocol | null;
  effective_protocol: AaaProtocol;
  protocol_source: "equipment" | "manufacturer";
  has_own_secret: boolean;
  secret_source: "equipment" | "manufacturer" | "none";
  has_own_tacacs_key: boolean;
  tacacs_key_source: "equipment" | "manufacturer" | "none";
  radius_require_message_authenticator: boolean;
  last_seen_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SystemUser {
  id: number;
  username: string;
  email: string;
  full_name: string;
  role: "superadmin" | "admin" | "operator" | "auditor";
  is_active: boolean;
  timezone: string;
  has_password: boolean;
  mfa_enabled: boolean;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SmtpSettings {
  id: number;
  host: string;
  port: number;
  username: string | null;
  has_password: boolean;
  use_tls: boolean;
  use_ssl: boolean;
  from_email: string;
  from_name: string | null;
  updated_at: string;
}

export interface AuthEvent {
  id: number;
  username: string;
  reply: string;
  authdate: string;
  accepted: boolean;
}

export interface CommandEvent {
  id: number;
  event_time: string;
  nasipaddress: string;
  nas_name: string | null;
  username: string;
  callingstationid: string;
  action: string;
  command: string;
  acctsessionid: string;
}

export interface Session {
  id: number;
  username: string;
  nasipaddress: string;
  nas_name: string | null;
  acctsessionid: string;
  acctstarttime: string | null;
  acctstoptime: string | null;
  acctsessiontime: number | null;
  acctinputoctets: number | null;
  acctoutputoctets: number | null;
  callingstationid: string;
  acctterminatecause: string;
  active: boolean;
}

export interface AuditEntry {
  id: number;
  created_at: string;
  actor_username: string | null;
  action: string;
  entity_type: string;
  entity_id: string | null;
  ip_address: string | null;
  before_json: string | null;
  after_json: string | null;
}


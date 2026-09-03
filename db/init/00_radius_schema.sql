-- ─────────────────────────────────────────────────────────────
-- Schema padrão do FreeRADIUS 3.2 para MySQL/MariaDB
-- Fonte: raddb/mods-config/sql/main/mysql/schema.sql
-- ─────────────────────────────────────────────────────────────
USE `radius`;

CREATE TABLE IF NOT EXISTS radacct (
  radacctid            bigint(21) NOT NULL AUTO_INCREMENT,
  acctsessionid        varchar(64) NOT NULL DEFAULT '',
  acctuniqueid         varchar(32) NOT NULL DEFAULT '',
  username             varchar(64) NOT NULL DEFAULT '',
  realm                varchar(64) DEFAULT '',
  nasipaddress         varchar(15) NOT NULL DEFAULT '',
  nasportid            varchar(32) DEFAULT NULL,
  nasporttype          varchar(32) DEFAULT NULL,
  acctstarttime        datetime NULL DEFAULT NULL,
  acctupdatetime       datetime NULL DEFAULT NULL,
  acctstoptime         datetime NULL DEFAULT NULL,
  acctinterval         int(12) DEFAULT NULL,
  acctsessiontime      int(12) unsigned DEFAULT NULL,
  acctauthentic        varchar(32) DEFAULT NULL,
  connectinfo_start    varchar(50) DEFAULT NULL,
  connectinfo_stop     varchar(50) DEFAULT NULL,
  acctinputoctets      bigint(20) DEFAULT NULL,
  acctoutputoctets     bigint(20) DEFAULT NULL,
  calledstationid      varchar(50) NOT NULL DEFAULT '',
  callingstationid     varchar(50) NOT NULL DEFAULT '',
  acctterminatecause   varchar(32) NOT NULL DEFAULT '',
  servicetype          varchar(32) DEFAULT NULL,
  framedprotocol       varchar(32) DEFAULT NULL,
  framedipaddress      varchar(15) NOT NULL DEFAULT '',
  framedipv6address    varchar(45) NOT NULL DEFAULT '',
  framedipv6prefix     varchar(45) NOT NULL DEFAULT '',
  framedinterfaceid    varchar(44) NOT NULL DEFAULT '',
  delegatedipv6prefix  varchar(45) NOT NULL DEFAULT '',
  class                varchar(64) DEFAULT NULL,
  PRIMARY KEY (radacctid),
  UNIQUE KEY acctuniqueid (acctuniqueid),
  KEY username (username),
  KEY framedipaddress (framedipaddress),
  KEY framedipv6address (framedipv6address),
  KEY framedipv6prefix (framedipv6prefix),
  KEY framedinterfaceid (framedinterfaceid),
  KEY delegatedipv6prefix (delegatedipv6prefix),
  KEY acctsessionid (acctsessionid),
  KEY acctsessiontime (acctsessiontime),
  KEY acctstarttime (acctstarttime),
  KEY acctstoptime (acctstoptime),
  KEY nasipaddress (nasipaddress),
  KEY class (class)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS radcheck (
  id       int(11) unsigned NOT NULL AUTO_INCREMENT,
  username varchar(64) NOT NULL DEFAULT '',
  attribute varchar(64) NOT NULL DEFAULT '',
  op       char(2) NOT NULL DEFAULT '==',
  value    varchar(253) NOT NULL DEFAULT '',
  PRIMARY KEY (id),
  KEY username (username(32))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS radgroupcheck (
  id        int(11) unsigned NOT NULL AUTO_INCREMENT,
  groupname varchar(64) NOT NULL DEFAULT '',
  attribute varchar(64) NOT NULL DEFAULT '',
  op        char(2) NOT NULL DEFAULT '==',
  value     varchar(253) NOT NULL DEFAULT '',
  PRIMARY KEY (id),
  KEY groupname (groupname(32))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS radgroupreply (
  id        int(11) unsigned NOT NULL AUTO_INCREMENT,
  groupname varchar(64) NOT NULL DEFAULT '',
  attribute varchar(64) NOT NULL DEFAULT '',
  op        char(2) NOT NULL DEFAULT '=',
  value     varchar(253) NOT NULL DEFAULT '',
  PRIMARY KEY (id),
  KEY groupname (groupname(32))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS radreply (
  id        int(11) unsigned NOT NULL AUTO_INCREMENT,
  username  varchar(64) NOT NULL DEFAULT '',
  attribute varchar(64) NOT NULL DEFAULT '',
  op        char(2) NOT NULL DEFAULT '=',
  value     varchar(253) NOT NULL DEFAULT '',
  PRIMARY KEY (id),
  KEY username (username(32))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS radusergroup (
  id        int(11) unsigned NOT NULL AUTO_INCREMENT,
  username  varchar(64) NOT NULL DEFAULT '',
  groupname varchar(64) NOT NULL DEFAULT '',
  priority  int(11) NOT NULL DEFAULT 1,
  PRIMARY KEY (id),
  KEY username (username(32))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS radpostauth (
  id             bigint(21) NOT NULL AUTO_INCREMENT,
  username       varchar(64) NOT NULL DEFAULT '',
  pass           varchar(64) NOT NULL DEFAULT '',
  reply          varchar(64) NOT NULL DEFAULT '',
  authdate       timestamp(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
  class          varchar(64) DEFAULT NULL,
  PRIMARY KEY (id),
  KEY username (username),
  KEY class (class),
  KEY authdate (authdate)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS nas (
  id          int(10) NOT NULL AUTO_INCREMENT,
  nasname     varchar(128) NOT NULL,
  shortname   varchar(32) DEFAULT NULL,
  type        varchar(30) DEFAULT 'other',
  ports       int(5) DEFAULT NULL,
  secret      varchar(60) DEFAULT 'secret',
  server      varchar(64) DEFAULT NULL,
  community   varchar(50) DEFAULT NULL,
  description varchar(200) DEFAULT 'RADIUS Client',
  PRIMARY KEY (id),
  KEY nasname (nasname)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS nasreload (
  nasipaddress varchar(15) NOT NULL,
  reloadtime   datetime NOT NULL,
  PRIMARY KEY (nasipaddress)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ─────────────────────────────────────────────────────────────
-- cmd_acct — contabilização de comandos (NÃO é schema padrão do FreeRADIUS).
-- Preenchida pelo site `default` (seção accounting) quando um Accounting-Request
-- traz o comando executado num VSA de fabricante. Alimenta as telas
-- Authorization e Accounting do painel. Ver também a migração Alembic 0007.
-- ─────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cmd_acct (
  id               bigint(21)   NOT NULL AUTO_INCREMENT,
  event_time       datetime     NOT NULL,
  nasipaddress     varchar(15)  NOT NULL DEFAULT '',
  username         varchar(64)  NOT NULL DEFAULT '',
  callingstationid varchar(50)  NOT NULL DEFAULT '',
  action           varchar(32)  NOT NULL DEFAULT '',
  command          varchar(512) NOT NULL DEFAULT '',
  acctsessionid    varchar(64)  NOT NULL DEFAULT '',
  PRIMARY KEY (id),
  KEY username (username(32)),
  KEY event_time (event_time),
  KEY nasipaddress (nasipaddress)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

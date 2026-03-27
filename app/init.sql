-- ─────────────────────────────────────────────
-- Task Manager — Database Schema
-- Updated: 2026 | taskdb
-- ─────────────────────────────────────────────

CREATE DATABASE IF NOT EXISTS taskdb;
USE taskdb;

-- ─────────────────────────────────────────────
-- USERS TABLE
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
  id                  INT AUTO_INCREMENT PRIMARY KEY,
  name                VARCHAR(100)  NOT NULL,
  email               VARCHAR(100)  NOT NULL UNIQUE,
  password_hash       VARCHAR(255)  NOT NULL,
  role                ENUM('manager','employee') NOT NULL DEFAULT 'employee',
  is_first_login      BOOLEAN       NOT NULL DEFAULT TRUE,
  reset_token         VARCHAR(100)  DEFAULT NULL,
  reset_token_expires DATETIME      DEFAULT NULL,
  created_at          TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────────
-- TASKS TABLE
-- ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS tasks (
  id          INT AUTO_INCREMENT PRIMARY KEY,
  title       VARCHAR(255)  NOT NULL,
  description TEXT,
  created_by  INT           DEFAULT NULL,
  assigned_to INT           DEFAULT NULL,
  status      ENUM('pending','done','redo') NOT NULL DEFAULT 'pending',
  s3_file_key VARCHAR(500)  DEFAULT NULL,
  created_at  TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (created_by)  REFERENCES users(id) ON DELETE SET NULL,
  FOREIGN KEY (assigned_to) REFERENCES users(id) ON DELETE SET NULL
);

-- ─────────────────────────────────────────────
-- DEFAULT MANAGER ACCOUNT
-- email:    haarisraja08@gmail.com
-- password: Admin@1234
-- ─────────────────────────────────────────────
INSERT INTO users (name, email, password_hash, role, is_first_login)
VALUES (
  'Hari Krishnan',
  'haarisraja08@gmail.com',
  'scrypt:32768:8:1$KBlTN2bU4oitw8zV$819d044d93526c651b96897eed64ef21e5b3429d57fd07a574a702d8cecca787f9ee70a0afedcabe4d47c3e3c1f17cf93839c3956a5a69155a51f732b3707bd2',
  'manager',
  FALSE
)
ON DUPLICATE KEY UPDATE
  name           = VALUES(name),
  role           = VALUES(role),
  is_first_login = VALUES(is_first_login);
-- =============================================================
-- SCHEMA - Gastos Prefeitura
-- =============================================================
CREATE DATABASE IF NOT EXISTS gastos_prefeitura
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE gastos_prefeitura;

-- Tabela principal de pagamentos
CREATE TABLE IF NOT EXISTS pagamentos (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    data             DATE,
    ano              SMALLINT,
    mes              TINYINT,
    descricao        TEXT,
    favorecido       VARCHAR(500),
    recurso          VARCHAR(200),
    conta            VARCHAR(200),
    valor            DECIMAL(15, 2),
    secretaria       VARCHAR(100),
    aba_origem       VARCHAR(100),
    arquivo_origem   VARCHAR(200),
    hash_linha       VARCHAR(64)  UNIQUE,   -- evita duplicatas
    importado_em     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ano_mes   (ano, mes),
    INDEX idx_favorecido (favorecido(100)),
    INDEX idx_recurso    (recurso(100))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Controle dos arquivos importados
CREATE TABLE IF NOT EXISTS arquivos_importados (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    nome_arquivo     VARCHAR(200) NOT NULL,
    hash_arquivo     VARCHAR(64),           -- SHA256 do arquivo
    total_linhas     INT,
    linhas_inseridas INT,
    linhas_duplicadas INT,
    status           ENUM('ok','erro','parcial') DEFAULT 'ok',
    mensagem         TEXT,
    importado_em     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Usuários do dashboard
CREATE TABLE IF NOT EXISTS usuarios (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    username         VARCHAR(100) UNIQUE NOT NULL,
    nome             VARCHAR(200),
    senha_hash       VARCHAR(255) NOT NULL,
    perfil           ENUM('admin', 'viewer') DEFAULT 'viewer',
    ativo            TINYINT(1) DEFAULT 1,
    criado_em        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ultimo_acesso    TIMESTAMP NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

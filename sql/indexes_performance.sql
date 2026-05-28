-- Índices adicionais para acelerar filtros e agregações comuns.
-- Idempotente: usa IF NOT EXISTS via stored procedure trick (MySQL 8+).

USE gastos_prefeitura;

-- Helper: cria índice só se não existir
DELIMITER //
DROP PROCEDURE IF EXISTS _add_index //
CREATE PROCEDURE _add_index(IN tbl VARCHAR(64), IN idx VARCHAR(64), IN cols VARCHAR(255))
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.statistics
    WHERE table_schema = DATABASE() AND table_name = tbl AND index_name = idx
  ) THEN
    SET @sql = CONCAT('CREATE INDEX ', idx, ' ON ', tbl, ' (', cols, ')');
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
  END IF;
END //
DELIMITER ;

-- Filtro por secretaria (muito usado)
CALL _add_index('pagamentos', 'idx_secretaria', 'secretaria(50)');

-- Última atualização (importado_em DESC)
CALL _add_index('pagamentos', 'idx_importado_em', 'importado_em');

-- Composto pra agregações por (secretaria, ano, mes)
CALL _add_index('pagamentos', 'idx_sec_ano_mes', 'secretaria(50), ano, mes');

-- Composto pra "top fornecedor por secretaria"
CALL _add_index('pagamentos', 'idx_sec_favorecido', 'secretaria(50), favorecido(100)');

-- Composto pra filtros de ano + favorecido (aba Por Fornecedor)
CALL _add_index('pagamentos', 'idx_ano_favorecido', 'ano, favorecido(100)');

DROP PROCEDURE _add_index;

-- Verificação
SELECT 'Indices na tabela pagamentos:' AS info;
SHOW INDEX FROM pagamentos;

-- Estatísticas de tabela
SELECT 'Tamanho:' AS info,
       TABLE_NAME,
       TABLE_ROWS,
       ROUND(DATA_LENGTH/1024/1024, 2) AS data_mb,
       ROUND(INDEX_LENGTH/1024/1024, 2) AS index_mb
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'gastos_prefeitura' AND TABLE_NAME = 'pagamentos';

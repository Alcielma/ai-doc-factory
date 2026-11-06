-- Migração idempotente: cadastro de empresas e vínculo do lote. Seguro rodar mais de uma vez.
CREATE TABLE IF NOT EXISTS empresa (
    id              BIGSERIAL PRIMARY KEY,
    nome            TEXT NOT NULL,
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS empresa_nome_uniq ON empresa (lower(btrim(nome)));

ALTER TABLE lote ADD COLUMN IF NOT EXISTS empresa_id BIGINT REFERENCES empresa(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS lote_empresa_idx ON lote (empresa_id);

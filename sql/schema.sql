-- Schema aplicado na primeira inicialização do Postgres (docker-entrypoint-initdb.d).
-- Os tipos documentais NÃO são restringidos aqui: a lista vive em app/config.py.

CREATE TABLE lote (
    id              BIGSERIAL PRIMARY KEY,
    sha256          CHAR(64) NOT NULL UNIQUE,          -- idempotência do upload
    nome_arquivo    TEXT NOT NULL,
    estado          TEXT NOT NULL DEFAULT 'recebido'
                    CHECK (estado IN ('recebido', 'ocr', 'classificando', 'concluido', 'erro')),
    docs_pendentes  INTEGER NOT NULL DEFAULT 0 CHECK (docs_pendentes >= 0),
    criado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE documento (
    id              BIGSERIAL PRIMARY KEY,
    lote_id         BIGINT NOT NULL REFERENCES lote(id) ON DELETE CASCADE,
    ordem           INTEGER NOT NULL,
    pagina_ini      INTEGER NOT NULL,
    pagina_fim      INTEGER NOT NULL,
    estado          TEXT NOT NULL DEFAULT 'segmentado'
                    CHECK (estado IN ('segmentado', 'classificado', 'em_revisao', 'revisado', 'erro')),
    tipo            TEXT,
    confianca       DOUBLE PRECISION,
    tipo_original   TEXT,                              -- tipo antes da correção humana
    revisor         TEXT,
    revisado_em     TIMESTAMPTZ,
    modelo          TEXT,
    versao_prompt   TEXT,
    probabilidades  JSONB,
    segmentacao_ambigua BOOLEAN NOT NULL DEFAULT false,  -- fronteira inicial decidida na faixa ambígua
    CHECK (pagina_fim >= pagina_ini),
    UNIQUE (lote_id, ordem)
);

CREATE TABLE pagina (
    id              BIGSERIAL PRIMARY KEY,
    lote_id         BIGINT NOT NULL REFERENCES lote(id) ON DELETE CASCADE,
    numero          INTEGER NOT NULL,
    documento_id    BIGINT REFERENCES documento(id) ON DELETE SET NULL,
    texto           TEXT,
    UNIQUE (lote_id, numero)
);

CREATE INDEX pagina_documento_idx ON pagina (documento_id);
CREATE INDEX pagina_texto_fts_idx ON pagina
    USING GIN (to_tsvector('portuguese', coalesce(texto, '')));

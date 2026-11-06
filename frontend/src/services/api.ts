import type { Company } from '../types';

const rawApiUrl = (import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000').trim().replace(/\/+$/, '');
const rawPrefix = (import.meta.env.VITE_API_PREFIX ?? '').trim();
const normalizedPrefix = rawPrefix ? (rawPrefix.startsWith('/') ? rawPrefix : `/${rawPrefix}`).replace(/\/+$/, '') : '';

export const BASE_URL = `${rawApiUrl}${normalizedPrefix}`;

export interface TipoInfo {
  slug: string;
  nome: string;
  icone: 'car' | 'hash' | 'idcard' | 'home' | 'file' | 'briefcase' | 'shield' | string;
}

export interface LoteResponse {
  lote_id: number;
  estado: string;
  existente: boolean;
  empresa_id?: number | null;
}

export interface DocumentoResponse {
  id: number;
  ordem: number;
  pagina_ini: number;
  pagina_fim: number;
  estado: string;
  tipo: string | null;
  confianca: number;
  segmentacao_ambigua: boolean;
  probabilidades: Record<string, number> | null;
  tipo_original: string | null;
}

export interface LoteStatusResponse {
  id: number;
  nome_arquivo: string;
  estado: string;
  docs_pendentes: number;
  empresa_id?: number | null;
  documentos: DocumentoResponse[];
}

export interface SearchResult {
  lote_id: number;
  pagina: number;
  trecho: string;
  documento_id?: number | null;
  tipo?: string | null;
  nome_arquivo?: string;
}

export interface ReviewQueueItem {
  id: number;
  lote_id: number;
  tipo_sugerido: string | null;
  confianca: number | null;
  motivo: string | null;
  imagem_url: string;
  pagina_ini: number;
  pagina_fim: number;
  campos: Record<string, string>;
  pessoa: string | null;
  nome_arquivo: string;
  n_paginas: number;
  processado_em: string;
}

export const apiService = {
  /**
   * Helper para construir a URL absoluta de uma imagem de página
   */
  getPageImageUrl: (loteId: number, pagina: number): string => {
    return `${BASE_URL}/lotes/${loteId}/paginas/${pagina}/imagem`;
  },

  /**
   * Lista os tipos documentais oficiais do backend (ordem, slug, nome, ícone)
   */
  getTipos: async (): Promise<TipoInfo[]> => {
    const response = await fetch(`${BASE_URL}/tipos`);
    if (!response.ok) {
      throw new Error('Erro ao listar tipos documentais');
    }
    return response.json();
  },

  /**
   * Faz upload de um arquivo para criar um novo lote
   */
  uploadLote: async (file: File, empresaId?: number): Promise<LoteResponse> => {
    const formData = new FormData();
    formData.append('arquivo', file);
    if (empresaId !== undefined && empresaId !== null) {
      formData.append('empresa_id', String(empresaId));
    }

    const response = await fetch(`${BASE_URL}/lotes`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Erro ao fazer upload do arquivo');
    }

    return response.json();
  },

  /**
   * Obtém o status e os documentos de um lote específico
   */
  getLoteStatus: async (loteId: number): Promise<LoteStatusResponse> => {
    const response = await fetch(`${BASE_URL}/lotes/${loteId}`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Erro ao obter status do lote');
    }

    return response.json();
  },

  /**
   * Realiza uma busca textual nos documentos processados
   */
  search: async (query: string, limit: number = 20): Promise<SearchResult[]> => {
    const params = new URLSearchParams({ q: query, limite: limit.toString() });
    const response = await fetch(`${BASE_URL}/busca?${params}`);

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Erro ao realizar busca');
    }

    return response.json();
  },

  /**
   * Obtém a fila de documentos que aguardam revisão manual
   */
  getReviewQueue: async (): Promise<ReviewQueueItem[]> => {
    const response = await fetch(`${BASE_URL}/revisao`);
    if (!response.ok) throw new Error('Erro ao obter fila de revisão');
    return response.json();
  },

  /**
   * Submete a revisão de classificação de um documento (o tipo deve ser o slug válido)
   */
  submitReview: async (documentoId: number, tipo: string, revisor: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/documentos/${documentoId}/revisao`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tipo, revisor }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Erro ao submeter revisão');
    }

    return response.json();
  },

  /**
   * Atualiza ou remove campos extraídos de um documento (humano)
   */
  updateDocumentCampos: async (
    documentoId: number,
    campos: Record<string, string | null>,
    revisor: string = 'Revisor Humano'
  ): Promise<any> => {
    const response = await fetch(`${BASE_URL}/documentos/${documentoId}/campos`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ campos, revisor }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Erro ao atualizar campos do documento');
    }

    return response.json();
  },

  /**
   * Altera o tipo de um documento já classificado/revisado
   */
  updateDocumentTipo: async (
    documentoId: number,
    tipo: string,
    revisor: string = 'Revisor Humano'
  ): Promise<any> => {
    const response = await fetch(`${BASE_URL}/documentos/${documentoId}/tipo`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tipo, revisor }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Erro ao alterar tipo do documento');
    }

    return response.json();
  },

  /**
   * Exclui um documento do banco
   */
  deleteDocumento: async (documentoId: number): Promise<void> => {
    const response = await fetch(`${BASE_URL}/documentos/${documentoId}`, {
      method: 'DELETE',
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Erro ao excluir documento');
    }
  },

  /**
   * Obtém os detalhes de um documento específico
   */
  getDocumentDetails: async (documentoId: number): Promise<any> => {
    const response = await fetch(`${BASE_URL}/documentos/${documentoId}`);
    if (!response.ok) throw new Error('Documento não encontrado');
    return response.json();
  },

  /**
   * Obtém os documentos agrupados por tipo
   */
  getDocumentosAgrupados: async (empresaId?: number, falhou?: boolean): Promise<{ grupos: any[] }> => {
    const params = new URLSearchParams();
    if (empresaId !== undefined && empresaId !== null) {
      params.append('empresa_id', String(empresaId));
    }
    if (falhou !== undefined && falhou !== null) {
      params.append('falhou', String(falhou));
    }
    const queryString = params.toString() ? `?${params.toString()}` : '';
    const response = await fetch(`${BASE_URL}/documentos${queryString}`);
    if (!response.ok) throw new Error('Erro ao listar documentos');
    return response.json();
  },

  /**
   * Obtém a análise de folha de ponto de um documento
   */
  getAnalisePonto: async (documentoId: number): Promise<any> => {
    const response = await fetch(`${BASE_URL}/documentos/${documentoId}/analise-ponto`);
    if (!response.ok) throw new Error('Análise não encontrada');
    return response.json();
  },

  /**
   * Obtém a lista de empresas e seus scores de conformidade
   */
  getEmpresas: async (): Promise<Company[]> => {
    const response = await fetch(`${BASE_URL}/empresas`);
    if (!response.ok) throw new Error('Erro ao listar empresas');
    return response.json();
  },

  /**
   * Obtém a conformidade detalhada de uma empresa (por CNPJ)
   */
  getConformidadeEmpresa: async (cnpj: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/empresas/${encodeURIComponent(cnpj)}/conformidade`);
    if (!response.ok) throw new Error('Conformidade da empresa não encontrada');
    return response.json();
  },

  /**
   * Verifica a saúde do backend
   */
  checkHealth: async (): Promise<{ status: string }> => {
    const response = await fetch(`${BASE_URL}/health`);
    if (!response.ok) throw new Error('Backend indisponível');
    return response.json();
  }
};

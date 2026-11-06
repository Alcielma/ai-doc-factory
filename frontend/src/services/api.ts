import type { Company } from '../types';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
const API_PREFIX = import.meta.env.VITE_API_PREFIX || '/api';

const BASE_URL = `${API_URL}${API_PREFIX}`;

export interface LoteResponse {
  lote_id: number;
  estado: string;
  existente: boolean;
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
  documentos: DocumentoResponse[];
}

export interface SearchResult {
  lote_id: number;
  pagina: number;
  trecho: string;
}

export const apiService = {
  /**
   * Faz upload de um arquivo para criar um novo lote
   */
  uploadLote: async (file: File): Promise<LoteResponse> => {
    const formData = new FormData();
    formData.append('arquivo', file);

    const response = await fetch(`${BASE_URL}/lotes`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
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
      const error = await response.json();
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
      const error = await response.json();
      throw new Error(error.detail || 'Erro ao realizar busca');
    }

    return response.json();
  },

  /**
   * Obtém a fila de documentos que aguardam revisão manual
   */
  getReviewQueue: async (): Promise<any[]> => {
    const response = await fetch(`${BASE_URL}/revisao`);
    if (!response.ok) throw new Error('Erro ao obter fila de revisão');
    return response.json();
  },

  /**
   * Submete a revisão de um documento
   */
  submitReview: async (documentoId: number, tipo: string, revisor: string): Promise<any> => {
    const response = await fetch(`${BASE_URL}/documentos/${documentoId}/revisao`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tipo, revisor }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Erro ao submeter revisão');
    }

    return response.json();
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
  getDocumentosAgrupados: async (empresaId?: number): Promise<{ grupos: any[] }> => {
    const params = empresaId ? `?empresa_id=${empresaId}` : '';
    const response = await fetch(`${BASE_URL}/documentos${params}`);
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
   * Verifica a saúde do backend
   */
  checkHealth: async (): Promise<{ status: string }> => {
    const response = await fetch(`${BASE_URL}/health`);
    if (!response.ok) throw new Error('Backend indisponível');
    return response.json();
  }
};

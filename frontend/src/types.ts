export interface DocumentCategory {
  id: string
  name: string
  count: number
  totalPercentage: number
  icon: 'car' | 'hash' | 'idcard' | 'home' | 'file' | 'briefcase' | 'shield'
  slug: string
  score?: number
  classificacao?: 'Regular' | 'Atenção' | 'Crítico'
  provisorio?: boolean
}

export interface Company {
  cnpj: string
  razao_social: string
  score: number
  classificacao: 'Regular' | 'Atenção' | 'Crítico'
  provisorio: boolean
  documentos_por_tipo: Record<string, number>
}

export interface DetailedDocument {
  id: string
  filename: string
  category: string
  personName: string
  pages: number
  processedDate: string
  confidence: number
  metadata: {
    registrationNumber?: string
    categoryType?: string
    expirationDate?: string
    cpfNumber?: string
    rgNumber?: string
    address?: string
  }
}

export interface ReviewPendingDocument {
  id: string
  loteId: number
  filename: string
  issueType: 'baixa_qualidade' | 'conteudo_ilegivel' | 'confiança_baixa'
  issueLabel: string
  timeAgo: string
  isPriority?: boolean
  processedDate: string
  pages: number
  startPage: number
  issueDescription: string
  suggestedType: string
  suggestedConfidence: number
  extractedFields: { key: string; value: string }[]
  personName: string
}

// Aliases para retrocompatibilidade
export type StoredDocument = DetailedDocument
export type ReviewDocument = ReviewPendingDocument

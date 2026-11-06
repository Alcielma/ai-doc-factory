import React, { useState, useMemo } from 'react'
import {
  Search,
  ChevronLeft,
  ChevronDown,
  FileText,
  AlertTriangle,
  CheckCircle,
  Clock,
  X,
} from 'lucide-react'
import type { DocumentCategory, DetailedDocument } from '../types'
import { apiService } from '../services/api'

interface CategoryPageProps {
  category: DocumentCategory
  documents: DetailedDocument[]
  onBack: () => void
}

const CategoryPage: React.FC<CategoryPageProps> = ({
  category,
  documents,
  onBack,
}) => {
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedPerson, setSelectedPerson] = useState('todas')
  const [selectedConfidence, setSelectedConfidence] = useState('todas')
  const [sortBy, setSortBy] = useState<'recentes' | 'antigos' | 'confianca'>('recentes')
  const [selectedDocAnalysis, setSelectedDocAnalysis] = useState<any | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)

  const handleShowAnalysis = async (docId: string) => {
    setIsAnalyzing(true)
    try {
      const analysis = await apiService.getAnalisePonto(Number(docId))
      setSelectedDocAnalysis(analysis)
    } catch (err) {
      console.error('Erro ao buscar análise:', err)
      alert('Análise de ponto ainda não disponível para este documento.')
    } finally {
      setIsAnalyzing(false)
    }
  }

  // Get unique person names for the dropdown
  const peopleList = useMemo(() => {
    const names = new Set(documents.map((d) => d.personName))
    return Array.from(names)
  }, [documents])

  // Filter documents based on inputs
  const filteredDocuments = useMemo(() => {
    return documents.filter((doc) => {
      // Search query across filename, personName, and metadata
      const query = searchTerm.toLowerCase()
      const matchesSearch =
        !query ||
        doc.filename.toLowerCase().includes(query) ||
        doc.personName.toLowerCase().includes(query) ||
        Object.values(doc.metadata).some(
          (val) => val && val.toLowerCase().includes(query)
        )

      // Person filter
      const matchesPerson =
        selectedPerson === 'todas' || doc.personName === selectedPerson

      // Confidence filter
      let matchesConfidence = true
      if (selectedConfidence === 'alta') {
        matchesConfidence = doc.confidence >= 0.85
      } else if (selectedConfidence === 'media') {
        matchesConfidence = doc.confidence >= 0.7 && doc.confidence < 0.85
      } else if (selectedConfidence === 'baixa') {
        matchesConfidence = doc.confidence < 0.7
      }

      return matchesSearch && matchesPerson && matchesConfidence
    })
  }, [documents, searchTerm, selectedPerson, selectedConfidence])

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Breadcrumbs */}
      <nav className="flex items-center gap-2 text-sm text-[#877991] dark:text-[#95849f]">
        <button
          onClick={onBack}
          className="hover:text-[#2d0a33] dark:hover:text-white transition-colors cursor-pointer"
        >
          Documentos
        </button>
        <span>&gt;</span>
        <span className="font-semibold text-[#2d0a33] dark:text-[#f8f5fc]">
          {category.name}
        </span>
      </nav>

      {/* Header: Title, Count & Action Buttons */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-[#2d0a33] dark:text-[#f8f5fc]">
            {category.name}
          </h1>
          <p className="text-sm text-[#6e6378] dark:text-[#a093a8] mt-1">
            {filteredDocuments.length} documento{filteredDocuments.length !== 1 ? 's' : ''}
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onBack}
            className="flex items-center gap-1.5 px-4 py-2 rounded-xl text-sm font-medium border border-[#e1d9e6] dark:border-[#35223e] bg-white dark:bg-[#1a1120] hover:bg-[#f8f5fa] dark:hover:bg-[#25162a] text-[#2d0a33] dark:text-[#eae0ee] shadow-2xs transition-colors cursor-pointer"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Voltar</span>
          </button>
        </div>
      </div>

      {/* Search Input for Category */}
      <div className="relative w-full">
        <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-[#8f8298] dark:text-[#7f7188]" />
        <input
          type="text"
          placeholder={`Buscar em ${category.name}: arquivo, pessoa, número...`}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full pl-11 pr-4 py-2.5 text-sm rounded-xl bg-white dark:bg-[#1a1120] border border-[#ebe5ef] dark:border-[#2f1e39] text-[#2d0a33] dark:text-[#f5edf9] placeholder-[#8f8298] dark:placeholder-[#776881] focus:outline-none focus:ring-1 focus:ring-[#9333ea] dark:focus:ring-[#c026d3] shadow-2xs transition-all"
        />
      </div>

      {/* Filter Row */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs sm:text-sm">
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {/* People Filter Dropdown */}
          <div className="relative">
            <select
              value={selectedPerson}
              onChange={(e) => setSelectedPerson(e.target.value)}
              className="appearance-none pl-3.5 pr-8 py-2 rounded-xl border border-[#ebe5ef] dark:border-[#2f1e39] bg-white dark:bg-[#1a1120] text-[#2d0a33] dark:text-[#e4d6eb] focus:outline-none cursor-pointer shadow-2xs font-medium"
            >
              <option value="todas">Todos</option>
              {peopleList.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-[#8f8298] absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>

          {/* Confidence Filter Dropdown */}
          <div className="relative">
            <select
              value={selectedConfidence}
              onChange={(e) => setSelectedConfidence(e.target.value)}
              className="appearance-none pl-3.5 pr-8 py-2 rounded-xl border border-[#ebe5ef] dark:border-[#2f1e39] bg-white dark:bg-[#1a1120] text-[#2d0a33] dark:text-[#e4d6eb] focus:outline-none cursor-pointer shadow-2xs font-medium"
            >
              <option value="todas">Toda confiança</option>
              <option value="alta">Alta (&gt; 85%)</option>
              <option value="media">Média (70% - 85%)</option>
              <option value="baixa">Baixa (&lt; 70%)</option>
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-[#8f8298] absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
          </div>
        </div>

        {/* Sort Dropdown */}
        <div className="relative self-end sm:self-auto">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as 'recentes' | 'antigos' | 'confianca')}
            className="appearance-none pl-3.5 pr-8 py-2 rounded-xl border border-[#ebe5ef] dark:border-[#2f1e39] bg-white dark:bg-[#1a1120] text-[#2d0a33] dark:text-[#e4d6eb] focus:outline-none cursor-pointer shadow-2xs font-medium"
          >
            <option value="recentes">Mais recentes</option>
            <option value="antigos">Mais antigos</option>
            <option value="confianca">Maior confiança</option>
          </select>
          <ChevronDown className="w-3.5 h-3.5 text-[#8f8298] absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none" />
        </div>
      </div>

      {/* Document Cards List */}
      <div className="space-y-3 pt-2">
        {filteredDocuments.length === 0 ? (
          <div className="py-16 text-center rounded-2xl border border-dashed border-[#ebe5ef] dark:border-[#2f1e39] bg-white/50 dark:bg-[#1a1120]/50">
            <FileText className="w-12 h-12 mx-auto text-[#a092a8] dark:text-[#5f5367] mb-2" />
            <p className="text-base font-semibold text-[#2d0a33] dark:text-white">
              Nenhum documento encontrado
            </p>
            <p className="text-xs text-[#8f8298] dark:text-[#7f7188] mt-1">
              Tente redefinir os filtros ou o termo de pesquisa.
            </p>
          </div>
        ) : (
          filteredDocuments.map((doc) => (
            <div
              key={doc.id}
              className="w-full rounded-2xl p-4 sm:p-5 border border-[#ebe5ef] dark:border-[#2f1e39] bg-white dark:bg-[#1a1120] hover:border-[#c026d3]/40 dark:hover:border-[#c026d3]/50 transition-all flex items-start gap-4 shadow-2xs"
            >
              {/* Document Icon Box */}
              <div className="w-10 h-10 rounded-xl bg-[#f5eff7] dark:bg-[#25152b] text-[#9333ea] dark:text-[#d67bf3] flex items-center justify-center shrink-0 mt-0.5">
                <FileText className="w-5 h-5 stroke-[1.8]" />
              </div>

              {/* Document Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2">
                  <h3 className="text-base font-bold text-[#2d0a33] dark:text-[#f8f5fc] truncate">
                    {doc.filename}
                  </h3>
                  
                  {/* Status de Auditoria (Integração com Goal 6 do Backend) */}
                  {category.id === 'folha_ponto' && (
                    <button
                      onClick={() => handleShowAnalysis(doc.id)}
                      className="shrink-0 flex items-center gap-1.5 px-2 py-1 rounded-lg text-[10px] font-bold bg-[#f3e8ff] dark:bg-[#2e1065] text-[#7e22ce] dark:text-[#d8b4fe] border border-[#e9d5ff] dark:border-[#4c1d95] hover:bg-[#e9d5ff] transition-colors"
                    >
                      <Search className="w-3 h-3" />
                      Auditoria
                    </button>
                  )}
                </div>
                <p className="text-xs sm:text-sm text-[#6e6378] dark:text-[#a093a8] mt-0.5">
                  {doc.personName} · {doc.pages} página{doc.pages > 1 ? 's' : ''} · Processado em {doc.processedDate} · Confiança {Math.round(doc.confidence * 100)}%
                </p>

                {/* Metadata Badges / Tags */}
                <div className="flex flex-wrap items-center gap-2 mt-3">
                  {doc.metadata.registrationNumber && (
                    <span className="px-2.5 py-1 rounded-lg text-xs font-medium bg-[#f6f2f8] dark:bg-[#25172d] text-[#5b4d67] dark:text-[#c4b5cd] border border-[#ece4f1] dark:border-[#382343]">
                      Nº de registro: {doc.metadata.registrationNumber}
                    </span>
                  )}
                  {doc.metadata.categoryType && (
                    <span className="px-2.5 py-1 rounded-lg text-xs font-medium bg-[#f6f2f8] dark:bg-[#25172d] text-[#5b4d67] dark:text-[#c4b5cd] border border-[#ece4f1] dark:border-[#382343]">
                      Categoria: {doc.metadata.categoryType}
                    </span>
                  )}
                  {doc.metadata.expirationDate && (
                    <span className="px-2.5 py-1 rounded-lg text-xs font-medium bg-[#f6f2f8] dark:bg-[#25172d] text-[#5b4d67] dark:text-[#c4b5cd] border border-[#ece4f1] dark:border-[#382343]">
                      Validade: {doc.metadata.expirationDate}
                    </span>
                  )}
                  {doc.metadata.cpfNumber && (
                    <span className="px-2.5 py-1 rounded-lg text-xs font-medium bg-[#f6f2f8] dark:bg-[#25172d] text-[#5b4d67] dark:text-[#c4b5cd] border border-[#ece4f1] dark:border-[#382343]">
                      CPF: {doc.metadata.cpfNumber}
                    </span>
                  )}
                  {doc.metadata.rgNumber && (
                    <span className="px-2.5 py-1 rounded-lg text-xs font-medium bg-[#f6f2f8] dark:bg-[#25172d] text-[#5b4d67] dark:text-[#c4b5cd] border border-[#ece4f1] dark:border-[#382343]">
                      RG: {doc.metadata.rgNumber}
                    </span>
                  )}
                  {doc.metadata.address && (
                    <span className="px-2.5 py-1 rounded-lg text-xs font-medium bg-[#f6f2f8] dark:bg-[#25172d] text-[#5b4d67] dark:text-[#c4b5cd] border border-[#ece4f1] dark:border-[#382343]">
                      Endereço: {doc.metadata.address}
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Modal de Auditoria de Ponto (Integração Goal 6) */}
      {selectedDocAnalysis && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="w-full max-w-2xl bg-white dark:bg-[#1a1120] rounded-2xl border border-[#ebe5ef] dark:border-[#2f1e39] shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
            <div className="p-6 border-b border-[#ebe5ef] dark:border-[#2f1e39] flex items-center justify-between bg-[#fbf9fc] dark:bg-[#1f1325]">
              <div>
                <h3 className="text-lg font-bold text-[#2d0a33] dark:text-[#f8f5fc]">Auditoria de Folha de Ponto</h3>
                <p className="text-xs text-[#6e6378] dark:text-[#a093a8]">Análise automatizada de riscos trabalhistas</p>
              </div>
              <button 
                onClick={() => setSelectedDocAnalysis(null)}
                className="p-2 rounded-xl hover:bg-[#f3e8ff] dark:hover:bg-[#2e1065] text-[#6e6378] dark:text-[#a093a8] transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 overflow-y-auto space-y-6">
              {/* Score Geral */}
              <div className="flex items-center justify-between p-4 rounded-2xl bg-[#f8f5fa] dark:bg-[#201326] border border-[#ece4f1] dark:border-[#382240]">
                <div className="flex items-center gap-3">
                  <div className={`w-12 h-12 rounded-full flex items-center justify-center text-white font-bold text-lg ${
                    selectedDocAnalysis.score_geral >= 85 ? 'bg-emerald-500' :
                    selectedDocAnalysis.score_geral >= 65 ? 'bg-amber-500' : 'bg-red-500'
                  }`}>
                    {selectedDocAnalysis.score_geral}%
                  </div>
                  <div>
                    <div className="text-sm font-bold text-[#2d0a33] dark:text-[#f8f5fc]">Score de Conformidade</div>
                    <div className="text-[10px] text-[#6e6378] dark:text-[#a093a8]">Baseado em 4 dimensões de risco</div>
                  </div>
                </div>
                {selectedDocAnalysis.requer_revisao && (
                  <span className="px-3 py-1 rounded-lg bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400 text-[10px] font-bold border border-red-200 dark:border-red-800">
                    Requer Revisão
                  </span>
                )}
              </div>

              {/* Divergências Encontradas */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-[#6e6378] dark:text-[#a093a8] uppercase tracking-wider">Divergências Identificadas</h4>
                {selectedDocAnalysis.divergencias && selectedDocAnalysis.divergencias.length > 0 ? (
                  <div className="grid gap-2">
                    {selectedDocAnalysis.divergencias.map((div: any, idx: number) => (
                      <div key={idx} className="flex items-start gap-3 p-3 rounded-xl border border-red-100 dark:border-red-900/20 bg-red-50/50 dark:bg-red-950/10">
                        <AlertTriangle className="w-4 h-4 text-red-500 shrink-0 mt-0.5" />
                        <div>
                          <div className="text-xs font-bold text-red-800 dark:text-red-300">{div.tipo.replace(/_/g, ' ')}</div>
                          <p className="text-[10px] text-red-700 dark:text-red-400 mt-0.5">{div.evidencia || 'Sem evidência detalhada'}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex items-center gap-2 p-3 rounded-xl border border-emerald-100 dark:border-emerald-900/20 bg-emerald-50/50 dark:bg-emerald-950/10">
                    <CheckCircle className="w-4 h-4 text-emerald-500" />
                    <span className="text-xs font-medium text-emerald-800 dark:text-emerald-300">Nenhuma divergência crítica encontrada</span>
                  </div>
                )}
              </div>

              {/* Análise da IA */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-[#6e6378] dark:text-[#a093a8] uppercase tracking-wider">Parecer da Auditoria (IA)</h4>
                <div className="p-4 rounded-xl border border-[#ebe5ef] dark:border-[#2f1e39] bg-white dark:bg-[#150c18] text-sm text-[#2d0a33] dark:text-[#f8f5fc] leading-relaxed italic">
                  "{selectedDocAnalysis.analise}"
                </div>
              </div>
            </div>
            
            <div className="p-4 border-t border-[#ebe5ef] dark:border-[#2f1e39] bg-[#fbf9fc] dark:bg-[#1f1325] flex justify-end">
              <button 
                onClick={() => setSelectedDocAnalysis(null)}
                className="px-6 py-2 rounded-xl bg-[#3e0b48] dark:bg-[#9917a2] text-white text-sm font-bold shadow-sm hover:opacity-90 transition-opacity"
              >
                Fechar
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Loading Overlay para Auditoria */}
      {isAnalyzing && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/20 backdrop-blur-[2px]">
          <div className="p-4 bg-white dark:bg-[#1a1120] rounded-2xl shadow-xl flex items-center gap-3 border border-[#ebe5ef] dark:border-[#2f1e39]">
            <Clock className="w-5 h-5 text-[#9333ea] animate-spin" />
            <span className="text-sm font-bold text-[#2d0a33] dark:text-white">Gerando relatório de auditoria...</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default CategoryPage

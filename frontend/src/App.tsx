import { useState, useEffect, useMemo, useCallback } from 'react'
import { Header } from './components/Header'
import { BackgroundWave } from './components/BackgroundWave'
import { UploadModal } from './components/UploadModal'
import HomePage from './pages/HomePage'
import CategoryPage from './pages/CategoryPage'
import ManualReviewPage, { type CategoryOption } from './pages/ManualReviewPage'
import { apiService, type TipoInfo } from './services/api'
import type { DocumentCategory, DetailedDocument, ReviewPendingDocument, Company } from './types'
import type { FilterType } from './components/FilterBar'

export function App() {
  // Theme state: defaults to true (Dark Mode)
  const [isDark, setIsDark] = useState<boolean>(() => {
    const saved = localStorage.getItem('theme')
    if (saved !== null) {
      return saved === 'dark'
    }
    return true // Default dark mode
  })

  // Navigation view state: 'home' | 'categoria' | 'revisao'
  const [currentView, setCurrentView] = useState<'home' | 'categoria' | 'revisao'>('home')

  // Data states
  const [tiposInfo, setTiposInfo] = useState<TipoInfo[]>([])
  const [categories, setCategories] = useState<DocumentCategory[]>([])
  const [detailedDocs, setDetailedDocs] = useState<DetailedDocument[]>([])
  const [reviewPendingDocs, setReviewPendingDocs] = useState<ReviewPendingDocument[]>([])
  const [companies, setCompanies] = useState<Company[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeProcessingLote, setActiveProcessingLote] = useState<{ id: number; filename: string } | null>(null)

  // Selected category when in 'categoria' view
  const [selectedCategory, setSelectedCategory] = useState<DocumentCategory | null>(null)

  // Home filtering & search states
  const [categorySearch, setCategorySearch] = useState<string>('')
  const [globalSearch, setGlobalSearch] = useState<string>('')
  const [filterType, setFilterType] = useState<FilterType>('todos')

  // Upload modal state
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false)

  // Synchronize dark mode class to <html>
  useEffect(() => {
    const root = document.documentElement
    if (isDark) {
      root.classList.add('dark')
      localStorage.setItem('theme', 'dark')
    } else {
      root.classList.remove('dark')
      localStorage.setItem('theme', 'light')
    }
  }, [isDark])

  // Centralized fetch/refresh data function
  const fetchData = useCallback(async (isInitial = false) => {
    if (isInitial) setIsLoading(true)
    setError(null)
    try {
      const [tiposData, empresasData, docsAgrupados, reviewData] = await Promise.all([
        apiService.getTipos().catch((e) => {
          console.warn('Não foi possível obter /tipos, usando fallback local:', e)
          return [
            { slug: 'aso', nome: 'ASO (Atestado de Saúde Ocupacional)', icone: 'file' },
            { slug: 'folha_pagamento', nome: 'Folha de pagamento', icone: 'briefcase' },
            { slug: 'folha_ponto', nome: 'Folha de ponto', icone: 'hash' },
            { slug: 'holerite', nome: 'Holerite', icone: 'idcard' },
            { slug: 'recibo_ferias', nome: 'Recibo de férias', icone: 'home' },
            { slug: 'atestado_medico', nome: 'Atestado médico', icone: 'file' },
            { slug: 'contrato_trabalho', nome: 'Contrato de trabalho', icone: 'briefcase' },
          ] as TipoInfo[]
        }),
        apiService.getEmpresas().catch((e) => {
          console.warn('Erro ao obter /empresas:', e)
          return [] as Company[]
        }),
        apiService.getDocumentosAgrupados(),
        apiService.getReviewQueue().catch((e) => {
          console.warn('Erro ao obter /revisao:', e)
          return []
        })
      ])

      setTiposInfo(tiposData)
      setCompanies(empresasData)

      // Mapa rápido de tipos cadastrados
      const tiposMap: Record<string, TipoInfo> = {}
      tiposData.forEach((t) => {
        tiposMap[t.slug] = t
      })

      // Mapa de contagens por tipo vindo de docsAgrupados
      const groupDocsMap: Record<string, any[]> = {}
      docsAgrupados.grupos.forEach((g: any) => {
        const key = g.tipo || 'desconhecido'
        groupDocsMap[key] = g.documentos || []
      })

      // Monta as categorias começando pelos tipos oficiais do backend
      const mappedCategories: DocumentCategory[] = tiposData.map((t) => {
        const docs = groupDocsMap[t.slug] || []
        const validIcon = (['car', 'hash', 'idcard', 'home', 'file', 'briefcase', 'shield'].includes(t.icone)
          ? t.icone
          : 'file') as DocumentCategory['icon']

        return {
          id: t.slug,
          slug: t.slug,
          name: t.nome,
          count: docs.length,
          totalPercentage: 0,
          icon: validIcon,
        }
      })

      // Adiciona categorias extras que existam nos documentos (ex: 'desconhecido' ou 'sem_tipo')
      docsAgrupados.grupos.forEach((g: any) => {
        const slug = g.tipo || 'desconhecido'
        if (!tiposMap[slug]) {
          mappedCategories.push({
            id: slug,
            slug,
            name: slug.toUpperCase().replace('_', ' '),
            count: g.total || (g.documentos || []).length,
            totalPercentage: 0,
            icon: 'file',
          })
        }
      })

      const totalDocs = mappedCategories.reduce((acc, cat) => acc + cat.count, 0)
      const categoriesWithPercentage = mappedCategories.map((cat) => ({
        ...cat,
        totalPercentage: totalDocs > 0 ? Math.round((cat.count / totalDocs) * 100) : 0,
      }))
      setCategories(categoriesWithPercentage)

      // Flatten all documents from groups
      const allDocs: DetailedDocument[] = docsAgrupados.grupos.flatMap((g: any) =>
        (g.documentos || []).map((d: any) => ({
          id: String(d.id),
          filename: d.nome_arquivo || `Documento #${d.id}`,
          category: d.tipo || 'desconhecido',
          personName: d.pessoa || d.campos?.nome || 'Não identificado',
          pages: d.n_paginas || (d.pagina_fim - d.pagina_ini + 1) || 1,
          processedDate: d.processado_em
            ? new Date(d.processado_em).toLocaleDateString('pt-BR')
            : 'Recentemente',
          confidence: typeof d.confianca === 'number' ? d.confianca : 1.0,
          metadata: {
            registrationNumber: d.campos?.numero_registro || '',
            categoryType: d.campos?.categoria || '',
            expirationDate: d.campos?.data_vencimento || '',
            cpfNumber: d.campos?.cpf || '',
            rgNumber: d.campos?.rg || '',
            address: d.campos?.endereco || '',
            matricula: d.campos?.matricula || '',
            dataAdmissao: d.campos?.data_admissao || '',
            dataExame: d.campos?.data_exame || '',
            dataTermino: d.campos?.data_termino || '',
            tipoPrazo: d.campos?.tipo_prazo || '',
            cnpjPrestadora: d.campos?.cnpj_prestadora || '',
            razaoSocial: d.campos?.razao_social_prestadora || '',
          },
        }))
      )
      setDetailedDocs(allDocs)

      // Map review queue
      const mappedReviewDocs: ReviewPendingDocument[] = reviewData.map((d: any) => {
        const tipoSlug = d.tipo_sugerido || 'desconhecido'
        const tipoObj = tiposMap[tipoSlug]
        const tipoNome = tipoObj ? tipoObj.nome : tipoSlug.toUpperCase().replace('_', ' ')
        const reason = d.motivo || 'Revisão pendente'

        return {
          id: String(d.id),
          loteId: d.lote_id,
          filename: d.nome_arquivo || `Documento #${d.id}`,
          issueType: 'confiança_baixa',
          issueLabel: reason,
          timeAgo: 'Recentemente',
          processedDate: d.processado_em
            ? new Date(d.processado_em).toLocaleDateString('pt-BR')
            : 'Recentemente',
          pages: d.n_paginas || (d.pagina_fim - d.pagina_ini + 1) || 1,
          startPage: d.pagina_ini,
          endPage: d.pagina_fim,
          imageUrl: d.imagem_url,
          issueDescription: reason,
          suggestedType: tipoNome,
          suggestedTypeSlug: tipoSlug,
          suggestedConfidence: typeof d.confianca === 'number' ? d.confianca : 0.5,
          extractedFields: Object.entries(d.campos || {}).map(([key, value]) => ({
            key,
            value: String(value),
          })),
          personName: d.pessoa || d.campos?.nome || 'Não identificado',
        }
      })
      setReviewPendingDocs(mappedReviewDocs)
    } catch (err) {
      console.error('Erro ao buscar dados do backend:', err)
      setError('Não foi possível carregar os dados do servidor.')
    } finally {
      if (isInitial) setIsLoading(false)
    }
  }, [])

  // Initial fetch on mount
  useEffect(() => {
    fetchData(true)
  }, [fetchData])

  // Polling para lotes em processamento
  useEffect(() => {
    if (!activeProcessingLote) return

    const interval = setInterval(async () => {
      try {
        const status = await apiService.getLoteStatus(activeProcessingLote.id)
        if (status.estado === 'concluido' || status.estado === 'erro') {
          setActiveProcessingLote(null)
          clearInterval(interval)
          await fetchData(false)
        }
      } catch (err) {
        console.warn('Erro ao consultar status do lote:', err)
      }
    }, 2500)

    return () => clearInterval(interval)
  }, [activeProcessingLote, fetchData])

  const toggleTheme = () => {
    setIsDark((prev) => !prev)
  }

  // Calculate dynamic stats
  const classifiedCount = useMemo(() => {
    return categories.reduce((acc, cat) => acc + cat.count, 0)
  }, [categories])

  const reviewCount = reviewPendingDocs.length

  const accuracyPercentage = useMemo(() => {
    const total = classifiedCount + reviewCount
    if (total === 0) return 100
    return Math.round((classifiedCount / total) * 100)
  }, [classifiedCount, reviewCount])

  // Available categories for review selection
  const availableReviewCategories: CategoryOption[] = useMemo(() => {
    return tiposInfo.map((t) => ({ slug: t.slug, name: t.nome }))
  }, [tiposInfo])

  // Filter categories for the Home view
  const filteredCategories = useMemo(() => {
    return categories.filter((cat) => {
      const matchesSearch =
        cat.name.toLowerCase().includes(categorySearch.toLowerCase()) ||
        cat.slug.toLowerCase().includes(categorySearch.toLowerCase())

      const matchesGlobal =
        !globalSearch ||
        cat.name.toLowerCase().includes(globalSearch.toLowerCase())

      if (filterType === 'com_documentos') {
        return matchesSearch && matchesGlobal && cat.count > 0
      }
      if (filterType === 'vazios') {
        return matchesSearch && matchesGlobal && cat.count === 0
      }
      return matchesSearch && matchesGlobal
    })
  }, [categories, categorySearch, globalSearch, filterType])

  // Open category page
  const handleOpenCategory = (category: DocumentCategory) => {
    setSelectedCategory(category)
    setCurrentView('categoria')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Open manual review page
  const handleOpenReview = () => {
    setCurrentView('revisao')
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Back to home view
  const handleBackToHome = () => {
    setCurrentView('home')
    setSelectedCategory(null)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  // Handle manual review approval with full field persistence
  const handleApproveReviewDoc = async (
    docId: string,
    finalCategorySlug: string,
    _personName: string,
    fields?: Record<string, string | null>
  ) => {
    try {
      // 1. Se houver campos alterados ou preenchidos, persiste no backend
      if (fields && Object.keys(fields).length > 0) {
        await apiService.updateDocumentCampos(Number(docId), fields, 'Revisor Humano')
      }

      // 2. Submete a revisão de classificação com o slug estrito
      await apiService.submitReview(Number(docId), finalCategorySlug, 'Revisor Humano')

      // 3. Remove imediatamente da fila local de revisão
      setReviewPendingDocs((prev) => prev.filter((d) => d.id !== docId))

      // 4. Sincroniza dados com o backend
      await fetchData(false)
    } catch (err) {
      console.error('Erro ao aprovar documento:', err)
      alert('Erro ao processar a aprovação do documento. Verifique a conexão com o servidor.')
    }
  }

  // Handle upload completion & initiate polling
  const handleUploadSuccess = (filename: string, loteId: number) => {
    console.log(`Lote ${loteId} (${filename}) enviado para processamento.`)
    setActiveProcessingLote({ id: loteId, filename })
  }

  // Active documents for the category view
  const categoryDocuments = useMemo(() => {
    if (!selectedCategory) return []
    return detailedDocs.filter((d) => d.category === selectedCategory.id)
  }, [detailedDocs, selectedCategory])

  return (
    <div className="min-h-screen bg-[#fbf9fc] dark:bg-[#140c17] text-[#2d0a33] dark:text-[#f7f3f9] relative font-sans antialiased transition-colors selection:bg-[#9333ea]/30 selection:text-white">
      {/* Background fluid wave */}
      <BackgroundWave />

      {/* Top Navbar */}
      <Header
        isDark={isDark}
        onToggleTheme={toggleTheme}
        onOpenUpload={() => setIsUploadModalOpen(true)}
        onOpenReview={handleOpenReview}
        reviewCount={reviewCount}
        activeTab={currentView === 'revisao' ? 'revisao' : 'documentos'}
        onSelectTab={(tab) => {
          if (tab === 'documentos') {
            handleBackToHome()
          } else if (tab === 'revisao') {
            handleOpenReview()
          }
        }}
        globalSearch={globalSearch}
        onGlobalSearchChange={setGlobalSearch}
      />

      {/* Processing Banner if polling active */}
      {activeProcessingLote && (
        <div className="bg-[#9333ea] text-white text-xs sm:text-sm font-semibold py-2 px-4 text-center shadow-sm flex items-center justify-center gap-2">
          <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
          <span>
            Processando <strong>{activeProcessingLote.filename}</strong> (Lote #{activeProcessingLote.id}) com OCR e IA...
          </span>
        </div>
      )}

      {/* Main Content Area */}
      <main className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10 relative z-10">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-20 space-y-4">
            <div className="w-12 h-12 border-4 border-[#9333ea] border-t-transparent rounded-full animate-spin"></div>
            <p className="text-[#6e6378] dark:text-[#a093a8] font-medium">Carregando dados do servidor...</p>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-20 space-y-4 text-center">
            <div className="w-16 h-16 bg-red-100 dark:bg-red-950/30 text-red-600 dark:text-red-400 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <h3 className="text-xl font-bold text-[#2d0a33] dark:text-white">{error}</h3>
            <button 
              onClick={() => fetchData(true)}
              className="px-6 py-2 bg-[#9333ea] text-white rounded-xl font-bold hover:bg-[#7e22ce] transition-colors"
            >
              Tentar novamente
            </button>
          </div>
        ) : (
          <>
            {/* VIEW 1: CATEGORIA ESPECÍFICA */}
            {currentView === 'categoria' && selectedCategory && (
              <CategoryPage
                category={selectedCategory}
                documents={categoryDocuments}
                onBack={handleBackToHome}
              />
            )}

            {/* VIEW 2: REVISÃO MANUAL */}
            {currentView === 'revisao' && (
              <ManualReviewPage
                documents={reviewPendingDocs}
                onBack={handleBackToHome}
                onApprove={handleApproveReviewDoc}
                availableCategories={availableReviewCategories}
              />
            )}

            {/* VIEW 3: HOME PRINCIPAL */}
            {currentView === 'home' && (
              <HomePage
                reviewCount={reviewCount}
                onOpenReview={handleOpenReview}
                classifiedCount={classifiedCount}
                accuracyPercentage={accuracyPercentage}
                categorySearch={categorySearch}
                onCategorySearchChange={setCategorySearch}
                filterType={filterType}
                onFilterChange={setFilterType}
                filteredCategories={filteredCategories}
                onOpenCategory={handleOpenCategory}
                companies={companies}
              />
            )}
          </>
        )}
      </main>

      {/* Upload Modal */}
      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onSuccessUpload={handleUploadSuccess}
        companies={companies}
      />
    </div>
  )
}

export default App

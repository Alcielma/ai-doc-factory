import { useState, useEffect, useMemo } from 'react'
import { Header } from './components/Header'
import { ManualReviewBanner } from './components/ManualReviewBanner'
import { MetricsCard } from './components/MetricsCard'
import { FilterBar, type FilterType } from './components/FilterBar'
import { FolderCard } from './components/FolderCard'
import { BackgroundWave } from './components/BackgroundWave'
import { CategoryView } from './components/CategoryView'
import { ManualReviewView } from './components/ManualReviewView'
import { UploadModal } from './components/UploadModal'
import {
  INITIAL_CATEGORIES,
  INITIAL_DETAILED_DOCUMENTS,
  INITIAL_REVIEW_PENDING_DOCUMENTS,
} from './data/mockData'
import type { DocumentCategory, DetailedDocument, ReviewPendingDocument } from './types'

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
  const [categories, setCategories] = useState<DocumentCategory[]>(INITIAL_CATEGORIES)
  const [detailedDocs, setDetailedDocs] = useState<DetailedDocument[]>(INITIAL_DETAILED_DOCUMENTS)
  const [reviewPendingDocs, setReviewPendingDocs] = useState<ReviewPendingDocument[]>(
    INITIAL_REVIEW_PENDING_DOCUMENTS
  )

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

  const toggleTheme = () => {
    setIsDark((prev) => !prev)
  }

  // Calculate dynamic stats based on state
  const classifiedCount = useMemo(() => {
    return categories.reduce((acc, cat) => acc + cat.count, 0)
  }, [categories])

  const reviewCount = reviewPendingDocs.length

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

  // Handle manual review approval
  const handleApproveReviewDoc = (
    docId: string,
    finalCategoryName: string,
    personName: string
  ) => {
    const docToApprove = reviewPendingDocs.find((d) => d.id === docId)
    if (!docToApprove) return

    // Remove from pending queue
    setReviewPendingDocs((prev) => prev.filter((d) => d.id !== docId))

    // Find category id corresponding to the name
    const targetCat =
      categories.find((c) => c.name.toLowerCase() === finalCategoryName.toLowerCase()) ||
      categories.find((c) => c.slug.toLowerCase() === finalCategoryName.toLowerCase()) ||
      categories[0]

    // Create new detailed document
    const newDoc: DetailedDocument = {
      id: `doc-${Date.now()}`,
      filename: docToApprove.filename,
      category: targetCat.id,
      personName: personName || docToApprove.personName || 'Sem nome informado',
      pages: docToApprove.pages,
      processedDate: 'Hoje',
      confidence: 1.0,
      metadata: {
        registrationNumber: '09817263541',
        categoryType: targetCat.id === 'cnh' ? 'B' : undefined,
      },
    }

    setDetailedDocs((prev) => [newDoc, ...prev])

    // Increment category count
    setCategories((prev) => {
      const next = prev.map((c) =>
        c.id === targetCat.id ? { ...c, count: c.count + 1 } : c
      )
      const newTotal = next.reduce((sum, item) => sum + item.count, 0)
      return next.map((c) => ({
        ...c,
        totalPercentage: newTotal > 0 ? Math.round((c.count / newTotal) * 100) : 0,
      }))
    })
  }

  // Handle upload completion
  const handleUploadSuccess = (filename: string) => {
    const targetCat = categories[0]
    const newDoc: DetailedDocument = {
      id: `doc-${Date.now()}`,
      filename: filename,
      category: targetCat.id,
      personName: 'Documento Importado',
      pages: 1,
      processedDate: 'Hoje',
      confidence: 0.95,
      metadata: {
        registrationNumber: '01298374652',
        categoryType: 'B',
      },
    }
    setDetailedDocs((prev) => [newDoc, ...prev])
    setCategories((prev) => {
      const next = prev.map((c, i) =>
        i === 0 ? { ...c, count: c.count + 1 } : c
      )
      const newTotal = next.reduce((sum, item) => sum + item.count, 0)
      return next.map((c) => ({
        ...c,
        totalPercentage: newTotal > 0 ? Math.round((c.count / newTotal) * 100) : 0,
      }))
    })
  }

  // Active documents for the category view
  const categoryDocuments = useMemo(() => {
    if (!selectedCategory) return []
    return detailedDocs.filter((d) => d.category === selectedCategory.id)
  }, [detailedDocs, selectedCategory])

  return (
    <div className="min-h-screen bg-[#fbf9fc] dark:bg-[#140c17] text-[#2d0a33] dark:text-[#f7f3f9] relative font-sans antialiased transition-colors selection:bg-[#9333ea]/30 selection:text-white">
      {/* Bernhoeft background fluid wave */}
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

      {/* Main Content Area */}
      <main className="max-w-[1440px] mx-auto px-4 sm:px-6 lg:px-8 py-8 sm:py-10 relative z-10">
        {/* VIEW 1: CATEGORIA ESPECÍFICA (Ex: CNH) */}
        {currentView === 'categoria' && selectedCategory && (
          <CategoryView
            category={selectedCategory}
            documents={categoryDocuments}
            onBack={handleBackToHome}
          />
        )}

        {/* VIEW 2: REVISÃO MANUAL */}
        {currentView === 'revisao' && (
          <ManualReviewView
            documents={reviewPendingDocs}
            onBack={handleBackToHome}
            onApprove={handleApproveReviewDoc}
            availableCategories={categories.map((c) => c.name)}
          />
        )}

        {/* VIEW 3: HOME PRINCIPAL (Pastas) */}
        {currentView === 'home' && (
          <div className="space-y-6 sm:space-y-8 animate-in fade-in duration-200">
            {/* Page Title & Subtitle */}
            <section className="space-y-1">
              <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-[#2d0a33] dark:text-[#fdfcfe]">
                Documentos
              </h1>
              <p className="text-sm sm:text-base text-[#6f6379] dark:text-[#9f91a6]">
                Documentos processados pela IA, organizados por tipo documental.
              </p>
            </section>

            {/* Manual Review Attention Banner */}
            {reviewCount > 0 && (
              <section>
                <ManualReviewBanner
                  count={reviewCount}
                  onReviewClick={handleOpenReview}
                />
              </section>
            )}

            {/* Global Metrics Summary Card */}
            <section>
              <MetricsCard
                classifiedCount={classifiedCount}
                accuracyPercentage={75}
                reviewCount={reviewCount}
              />
            </section>

            {/* Category Search & Filter Tabs */}
            <section className="pt-2">
              <FilterBar
                searchCategory={categorySearch}
                onSearchChange={setCategorySearch}
                activeFilter={filterType}
                onFilterChange={setFilterType}
              />
            </section>

            {/* Document Folders Grid - Foco baseado na movimentação do mouse */}
            <section>
              {filteredCategories.length === 0 ? (
                <div className="w-full py-16 text-center rounded-2xl border border-dashed border-[#dcd4e2] dark:border-[#33203e] bg-white/50 dark:bg-[#1a1120]/50">
                  <p className="text-base font-semibold text-[#2d0a33] dark:text-white">
                    Nenhuma categoria encontrada
                  </p>
                  <p className="text-xs text-[#8f8298] dark:text-[#7f7188] mt-1">
                    Tente buscar por outro termo ou limpe os filtros.
                  </p>
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-5 sm:gap-6 auto-rows-fr">
                  {filteredCategories.map((category) => (
                    <FolderCard
                      key={category.id}
                      category={category}
                      isSelected={false}
                      onClick={handleOpenCategory}
                    />
                  ))}
                </div>
              )}
            </section>
          </div>
        )}
      </main>

      {/* Upload Modal */}
      <UploadModal
        isOpen={isUploadModalOpen}
        onClose={() => setIsUploadModalOpen(false)}
        onSuccessUpload={handleUploadSuccess}
      />
    </div>
  )
}

export default App

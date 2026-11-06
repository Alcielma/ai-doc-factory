import React from 'react'
import { ManualReviewBanner } from '../components/ManualReviewBanner'
import { MetricsCard } from '../components/MetricsCard'
import { FilterBar, type FilterType } from '../components/FilterBar'
import { FolderCard } from '../components/FolderCard'
import type { DocumentCategory } from '../types'

interface HomePageProps {
  reviewCount: number
  onOpenReview: () => void
  classifiedCount: number
  categorySearch: string
  onCategorySearchChange: (value: string) => void
  filterType: FilterType
  onFilterChange: (value: FilterType) => void
  filteredCategories: DocumentCategory[]
  onOpenCategory: (category: DocumentCategory) => void
}

const HomePage: React.FC<HomePageProps> = ({
  reviewCount,
  onOpenReview,
  classifiedCount,
  categorySearch,
  onCategorySearchChange,
  filterType,
  onFilterChange,
  filteredCategories,
  onOpenCategory,
}) => {
  return (
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
            onReviewClick={onOpenReview}
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
          onSearchChange={onCategorySearchChange}
          activeFilter={filterType}
          onFilterChange={onFilterChange}
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
                onClick={onOpenCategory}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

export default HomePage

import React from 'react'
import { Search } from 'lucide-react'

export type FilterType = 'todos' | 'com_documentos' | 'vazios'

interface FilterBarProps {
  searchCategory: string
  onSearchChange: (value: string) => void
  activeFilter: FilterType
  onFilterChange: (filter: FilterType) => void
}

export const FilterBar: React.FC<FilterBarProps> = ({
  searchCategory,
  onSearchChange,
  activeFilter,
  onFilterChange,
}) => {
  return (
    <div className="w-full flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
      {/* Category Search Input */}
      <div className="relative flex-1 max-w-md">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-[#8f8298] dark:text-[#7f7188]" />
        <input
          type="text"
          placeholder="Buscar categoria pelo nome"
          value={searchCategory}
          onChange={(e) => onSearchChange(e.target.value)}
          className="w-full pl-10 pr-4 py-2 text-sm rounded-xl bg-white dark:bg-[#1a1120] border border-[#ebe5ef] dark:border-[#2f1e39] text-[#2d0a33] dark:text-[#f5edf9] placeholder-[#8f8298] dark:placeholder-[#776881] focus:outline-none focus:ring-1 focus:ring-[#9333ea] dark:focus:ring-[#c026d3] transition-all"
        />
      </div>

      {/* Filter Tabs */}
      <div className="inline-flex items-center p-1 rounded-xl bg-[#f5f1f7] dark:bg-[#1a1120] border border-[#ebe5ef] dark:border-[#2f1e39] self-start sm:self-auto">
        <button
          type="button"
          onClick={() => onFilterChange('todos')}
          className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all cursor-pointer ${
            activeFilter === 'todos'
              ? 'bg-white dark:bg-[#321c3b] text-[#2d0a33] dark:text-white shadow-xs font-semibold'
              : 'text-[#6e6378] dark:text-[#9789a1] hover:text-[#2d0a33] dark:hover:text-white'
          }`}
        >
          Todos os tipos
        </button>

        <button
          type="button"
          onClick={() => onFilterChange('com_documentos')}
          className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all cursor-pointer ${
            activeFilter === 'com_documentos'
              ? 'bg-white dark:bg-[#321c3b] text-[#2d0a33] dark:text-white shadow-xs font-semibold'
              : 'text-[#6e6378] dark:text-[#9789a1] hover:text-[#2d0a33] dark:hover:text-white'
          }`}
        >
          Com documentos
        </button>

        <button
          type="button"
          onClick={() => onFilterChange('vazios')}
          className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all cursor-pointer ${
            activeFilter === 'vazios'
              ? 'bg-white dark:bg-[#321c3b] text-[#2d0a33] dark:text-white shadow-xs font-semibold'
              : 'text-[#6e6378] dark:text-[#9789a1] hover:text-[#2d0a33] dark:hover:text-white'
          }`}
        >
          Vazios
        </button>
      </div>
    </div>
  )
}


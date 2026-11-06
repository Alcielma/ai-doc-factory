import React from 'react'

interface MetricsCardProps {
  classifiedCount: number
  accuracyPercentage: number
  reviewCount: number
}

export const MetricsCard: React.FC<MetricsCardProps> = ({
  classifiedCount,
  accuracyPercentage,
  reviewCount,
}) => {
  return (
    <div className="w-full rounded-2xl bg-white dark:bg-[#1a1120] border border-[#ebe5ef] dark:border-[#2f1e39] shadow-xs p-6 sm:p-7 transition-colors">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-0 md:divide-x md:divide-[#efeaf3] md:dark:divide-[#2f1f3a]">
        {/* Metric 1: Documentos Classificados */}
        <div className="flex flex-col justify-center md:pr-8">
          <div className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-[#6d1b72] dark:text-[#f2c7f9]">
            {classifiedCount}
          </div>
          <div className="text-sm font-medium text-[#6e6378] dark:text-[#a093a8] mt-2">
            documentos classificados
          </div>
        </div>

        {/* Metric 2: Taxa IA limpa, sem highlight */}
        <div className="flex flex-col justify-center md:px-8">
          <div className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-[#6d1b72] dark:text-[#f2c7f9]">
            {accuracyPercentage}%
          </div>
          <div className="text-sm font-medium text-[#6e6378] dark:text-[#a093a8] mt-2">
            classificados automaticamente pela IA
          </div>
        </div>

        {/* Metric 3: Aguardando Revisão */}
        <div className="flex flex-col justify-center md:pl-8">
          <div className="text-3xl sm:text-4xl lg:text-5xl font-black tracking-tight text-[#6d1b72] dark:text-[#f2c7f9]">
            {reviewCount}
          </div>
          <div className="text-sm font-medium text-[#6e6378] dark:text-[#a093a8] mt-2">
            aguardando revisão
          </div>
        </div>
      </div>
    </div>
  )
}

import React, { useState } from 'react'
import { X, UploadCloud, File, CheckCircle2, Loader2 } from 'lucide-react'

interface UploadModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccessUpload: (filename: string) => void
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onSuccessUpload,
}) => {
  const [file, setFile] = useState<File | null>(null)
  const [isUploading, setIsUploading] = useState(false)
  const [isSuccess, setIsSuccess] = useState(false)

  if (!isOpen) return null

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setFile(e.target.files[0])
    }
  }

  const handleUpload = () => {
    if (!file) return
    setIsUploading(true)
    setTimeout(() => {
      setIsUploading(false)
      setIsSuccess(true)
      setTimeout(() => {
        onSuccessUpload(file.name)
        setIsSuccess(false)
        setFile(null)
        onClose()
      }, 1200)
    }, 1500)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-xs">
      <div className="w-full max-w-md rounded-2xl bg-white dark:bg-[#1a1120] border border-[#ebe5ef] dark:border-[#2f1e39] p-6 shadow-2xl relative animate-in fade-in zoom-in-95 duration-200">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 p-1.5 rounded-lg text-[#6e6378] dark:text-[#a093a8] hover:bg-[#f5eef7] dark:hover:bg-[#281831] transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <h3 className="text-lg font-bold text-[#2d0a33] dark:text-[#f8f5fc]">
          Enviar Lote de Documentos
        </h3>
        <p className="text-xs text-[#6e6378] dark:text-[#9f91a6] mt-0.5">
          Faça o upload de arquivos PDF para segmentação e classificação automática por IA
        </p>

        {isSuccess ? (
          <div className="my-8 text-center">
            <CheckCircle2 className="w-14 h-14 mx-auto text-emerald-500 mb-2 animate-bounce" />
            <h4 className="font-bold text-base text-[#2d0a33] dark:text-white">
              Lote enviado com sucesso!
            </h4>
            <p className="text-xs text-[#6e6378] dark:text-[#9f91a6] mt-1">
              O pipeline de OCR e IA está processando as páginas.
            </p>
          </div>
        ) : (
          <div className="mt-5 space-y-4">
            <label className="border-2 border-dashed border-[#dcd4e2] dark:border-[#3d2948] hover:border-[#9333ea] dark:hover:border-[#c026d3] rounded-2xl p-6 flex flex-col items-center justify-center cursor-pointer transition-colors bg-[#fdfbfe] dark:bg-[#150c18]">
              <UploadCloud className="w-10 h-10 text-[#9333ea] dark:text-[#c026d3] mb-2" />
              <span className="text-sm font-semibold text-[#2d0a33] dark:text-white">
                Clique ou arraste um PDF
              </span>
              <span className="text-xs text-[#8f8298] dark:text-[#7f7188] mt-1">
                Lotes escaneados com até 100 páginas (máx. 50MB)
              </span>
              <input
                type="file"
                accept=".pdf"
                className="hidden"
                onChange={handleFileChange}
              />
            </label>

            {file && (
              <div className="p-3 rounded-xl bg-[#f6ebfa] dark:bg-[#281530] border border-[#d88cf5]/40 dark:border-[#c026d3]/40 flex items-center justify-between">
                <div className="flex items-center gap-2 overflow-hidden">
                  <File className="w-4 h-4 text-[#9333ea] dark:text-[#d67bf3] shrink-0" />
                  <span className="text-xs font-semibold text-[#2d0a33] dark:text-white truncate">
                    {file.name}
                  </span>
                </div>
                <span className="text-[11px] text-[#8f8298] dark:text-[#9f91a6] shrink-0">
                  {(file.size / (1024 * 1024)).toFixed(2)} MB
                </span>
              </div>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl text-xs sm:text-sm font-medium text-[#6e6378] dark:text-[#a093a8] hover:bg-[#f5eef7] dark:hover:bg-[#281831] transition-colors cursor-pointer"
              >
                Cancelar
              </button>
              <button
                type="button"
                disabled={!file || isUploading}
                onClick={handleUpload}
                className="px-5 py-2 rounded-xl text-xs sm:text-sm font-bold text-white bg-[#3e0b48] hover:bg-[#52105e] dark:bg-[#9917a2] dark:hover:bg-[#b01ebb] disabled:opacity-50 flex items-center gap-2 shadow-sm transition-all cursor-pointer"
              >
                {isUploading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Processando...</span>
                  </>
                ) : (
                  <span>Enviar para IA</span>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}


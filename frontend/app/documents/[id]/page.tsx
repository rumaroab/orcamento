'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'

interface DocumentSummary {
  document_id: string
  year: number
  revenue_total: number
  expense_total: number
  revenue_by_category: CategorySummary[]
  expense_by_category: CategorySummary[]
}

interface CategorySummary {
  category: string
  total_value: number
  item_count: number
}

interface ImportJob {
  id: string
  status: string
  progress: number
  error_message: string | null
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

export default function DocumentPage() {
  const params = useParams()
  const router = useRouter()
  const documentId = params.id as string
  
  const [summary, setSummary] = useState<DocumentSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [jobs, setJobs] = useState<ImportJob[]>([])
  const [archiving, setArchiving] = useState(false)

  useEffect(() => {
    fetchSummary()
    fetchJobs()
    // Poll for job updates if processing
    const interval = setInterval(() => {
      fetchJobs()
      fetchSummary()
    }, 2000)
    return () => clearInterval(interval)
  }, [documentId])

  const fetchSummary = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/documents/${documentId}/summary`)
      if (res.ok) {
        const data = await res.json()
        setSummary(data)
      }
    } catch (error) {
      console.error('Error fetching summary:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchJobs = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/documents/${documentId}/import-jobs`)
      if (res.ok) {
        const data = await res.json()
        setJobs(data)
      }
    } catch (error) {
      console.error('Error fetching jobs:', error)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('pt-PT', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  const formatPercentage = (value: number, total: number) => {
    if (total === 0) return '0%'
    return `${((value / total) * 100).toFixed(1)}%`
  }

  const handleArchive = async (archive: boolean) => {
    if (!confirm(`Tem a certeza que deseja ${archive ? 'arquivar' : 'desarquivar'} este documento?`)) {
      return
    }

    setArchiving(true)
    try {
      const res = await fetch(
        `${API_BASE}/api/documents/${documentId}/archive?archived=${archive}`,
        { method: 'PATCH' }
      )
      if (res.ok) {
        alert(`Documento ${archive ? 'arquivado' : 'desarquivado'} com sucesso`)
        router.push('/')
      } else {
        alert('Falha ao atualizar documento')
      }
    } catch (error) {
      console.error('Archive error:', error)
      alert('Falha ao atualizar documento')
    } finally {
      setArchiving(false)
    }
  }

  const activeJob = jobs.find(j => j.status === 'PENDING' || j.status === 'RUNNING')

  const getSideLabel = (side: string) => {
    return side === 'REVENUE' ? 'RECEITA' : 'DESPESA'
  }

  if (loading) {
    return <div className="min-h-screen p-8">A carregar...</div>
  }

  if (!summary) {
    return (
      <div className="min-h-screen p-8">
        <p>Documento não encontrado ou ainda em processamento</p>
        <Link href="/" className="text-blue-600">← Voltar ao início</Link>
      </div>
    )
  }

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-6xl mx-auto">
        <Link href="/" className="text-blue-600 mb-4 inline-block">← Voltar ao início</Link>
        
        <div className="flex justify-between items-center mb-4">
          <h1 className="text-4xl font-bold">Orçamento {summary.year}</h1>
          <button
            onClick={() => handleArchive(true)}
            disabled={archiving}
            className="bg-yellow-600 text-white px-4 py-2 rounded-md hover:bg-yellow-700 disabled:opacity-50"
          >
            {archiving ? 'A arquivar...' : 'Arquivar Documento'}
          </button>
        </div>
        
        {/* Processing Status */}
        {activeJob && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
            <h3 className="font-semibold mb-2">A Processar Documento</h3>
            <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
              <div
                className="bg-blue-600 h-2.5 rounded-full transition-all"
                style={{ width: `${activeJob.progress}%` }}
              />
            </div>
            <p className="text-sm text-gray-600">
              Estado: {activeJob.status} • Progresso: {activeJob.progress}%
            </p>
            {activeJob.error_message && (
              <p className="text-sm text-red-600 mt-2">Erro: {activeJob.error_message}</p>
            )}
          </div>
        )}

        {/* Totals */}
        <div className="grid grid-cols-2 gap-6 mb-8">
          <div className="bg-green-50 border border-green-200 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-green-800 mb-2">Total de Receitas</h2>
            <p className="text-3xl font-bold text-green-900">
              {formatCurrency(summary.revenue_total)}
            </p>
          </div>
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-red-800 mb-2">Total de Despesas</h2>
            <p className="text-3xl font-bold text-red-900">
              {formatCurrency(summary.expense_total)}
            </p>
          </div>
        </div>

        {/* Revenue Categories */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-2xl font-semibold mb-4">Receitas por Categoria</h2>
          {summary.revenue_by_category.length === 0 ? (
            <p className="text-gray-500">Nenhum item de receita encontrado</p>
          ) : (
            <div className="space-y-2">
              {summary.revenue_by_category
                .sort((a, b) => b.total_value - a.total_value)
                .map((cat) => (
                  <Link
                    key={cat.category}
                    href={`/documents/${documentId}/category/${encodeURIComponent(cat.category)}`}
                    className="block p-4 border rounded-md hover:bg-gray-50"
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <h3 className="font-semibold">{cat.category}</h3>
                        <p className="text-sm text-gray-500">
                          {cat.item_count} itens • {formatPercentage(cat.total_value, summary.revenue_total)} do total
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-semibold text-green-700">
                          {formatCurrency(cat.total_value)}
                        </p>
                      </div>
                    </div>
                  </Link>
                ))}
            </div>
          )}
        </div>

        {/* Expense Categories */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-semibold mb-4">Despesas por Categoria</h2>
          {summary.expense_by_category.length === 0 ? (
            <p className="text-gray-500">Nenhum item de despesa encontrado</p>
          ) : (
            <div className="space-y-2">
              {summary.expense_by_category
                .sort((a, b) => b.total_value - a.total_value)
                .map((cat) => (
                  <Link
                    key={cat.category}
                    href={`/documents/${documentId}/category/${encodeURIComponent(cat.category)}`}
                    className="block p-4 border rounded-md hover:bg-gray-50"
                  >
                    <div className="flex justify-between items-center">
                      <div>
                        <h3 className="font-semibold">{cat.category}</h3>
                        <p className="text-sm text-gray-500">
                          {cat.item_count} itens • {formatPercentage(cat.total_value, summary.expense_total)} do total
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="font-semibold text-red-700">
                          {formatCurrency(cat.total_value)}
                        </p>
                      </div>
                    </div>
                  </Link>
                ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}


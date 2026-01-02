'use client'

import { useState, useEffect } from 'react'
import { useParams } from 'next/navigation'
import Link from 'next/link'

interface BudgetItem {
  id: string
  document_id: string
  year: number
  side: string
  category: string
  description_original: string
  value: number | null
  unit: string
  page_number: number
  evidence_text: string
  explanation: string
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

export default function ItemPage() {
  const params = useParams()
  const itemId = params.id as string
  
  const [item, setItem] = useState<BudgetItem | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchItem()
  }, [itemId])

  const fetchItem = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/items/${itemId}`)
      if (res.ok) {
        const data = await res.json()
        setItem(data)
      }
    } catch (error) {
      console.error('Error fetching item:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value: number | null, unit: string) => {
    if (value === null) return 'N/A'
    return new Intl.NumberFormat('pt-PT', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value)
  }

  const getSideLabel = (side: string) => {
    return side === 'REVENUE' ? 'RECEITA' : 'DESPESA'
  }

  const viewSource = () => {
    if (!item) return
    const pdfUrl = `${API_BASE}/api/documents/${item.document_id}/pdf?page=${item.page_number}`
    window.open(pdfUrl, '_blank')
  }

  if (loading) {
    return <div className="min-h-screen p-8">A carregar...</div>
  }

  if (!item) {
    return (
      <div className="min-h-screen p-8">
        <p>Item não encontrado</p>
        <Link href="/" className="text-blue-600">← Voltar ao início</Link>
      </div>
    )
  }

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-4xl mx-auto">
        <Link
          href={`/documents/${item.document_id}/category/${encodeURIComponent(item.category)}`}
          className="text-blue-600 mb-4 inline-block"
        >
          ← Voltar a {item.category}
        </Link>
        
        <div className="bg-white rounded-lg shadow p-8">
          <div className="mb-6">
            <span className={`inline-block px-3 py-1 rounded-full text-sm font-semibold ${
              item.side === 'REVENUE' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
            }`}>
              {getSideLabel(item.side)}
            </span>
            <span className="ml-2 inline-block px-3 py-1 rounded-full text-sm bg-gray-100 text-gray-800">
              {item.category}
            </span>
          </div>

          <h1 className="text-3xl font-bold mb-4">{item.description_original}</h1>
          
          <div className="mb-6">
            <p className="text-4xl font-bold mb-2">
              {formatCurrency(item.value, item.unit)}
            </p>
            <p className="text-sm text-gray-500">Unidade: {item.unit}</p>
          </div>

          <div className="mb-6">
            <h2 className="text-xl font-semibold mb-2">Explicação</h2>
            <p className="text-gray-700 leading-relaxed">{item.explanation}</p>
          </div>

          <div className="mb-6 p-4 bg-gray-50 rounded-lg">
            <h2 className="text-xl font-semibold mb-2">Evidência</h2>
            <p className="text-gray-700 italic mb-2">"{item.evidence_text}"</p>
            <p className="text-sm text-gray-500">Fonte: Página {item.page_number}</p>
          </div>

          <button
            onClick={viewSource}
            className="bg-blue-600 text-white px-6 py-3 rounded-md hover:bg-blue-700"
          >
            Ver PDF Original (Página {item.page_number})
          </button>
        </div>
      </div>
    </div>
  )
}


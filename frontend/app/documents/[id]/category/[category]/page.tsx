'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
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

export default function CategoryPage() {
  const params = useParams()
  const router = useRouter()
  const documentId = params.id as string
  const category = decodeURIComponent(params.category as string)
  
  const [items, setItems] = useState<BudgetItem[]>([])
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState('value')

  useEffect(() => {
    fetchItems()
  }, [documentId, category, sortBy])

  const fetchItems = async () => {
    try {
      const res = await fetch(
        `${API_BASE}/api/documents/${documentId}/categories/${encodeURIComponent(category)}?sort_by=${sortBy}`
      )
      if (res.ok) {
        const data = await res.json()
        setItems(data)
      }
    } catch (error) {
      console.error('Error fetching items:', error)
    } finally {
      setLoading(false)
    }
  }

  const formatCurrency = (value: number | null, unit: string) => {
    if (value === null) return 'N/A'
    const numValue = value
    return new Intl.NumberFormat('pt-PT', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(numValue)
  }

  const total = items.reduce((sum, item) => sum + (item.value || 0), 0)

  if (loading) {
    return <div className="min-h-screen p-8">A carregar...</div>
  }

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-6xl mx-auto">
        <Link href={`/documents/${documentId}`} className="text-blue-600 mb-4 inline-block">
          ← Voltar ao documento
        </Link>
        
        <h1 className="text-4xl font-bold mb-2">{category}</h1>
        <p className="text-gray-600 mb-6">
          {items.length} itens • Total: {formatCurrency(total, 'EUR')}
        </p>

        {/* Sort Controls */}
        <div className="mb-4">
          <label className="mr-2">Ordenar por:</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="px-4 py-2 border rounded-md"
          >
            <option value="value">Valor (maior para menor)</option>
            <option value="page_number">Número da página</option>
            <option value="description">Descrição</option>
          </select>
        </div>

        {/* Items List */}
        <div className="space-y-4">
          {items.length === 0 ? (
            <p className="text-gray-500">Nenhum item encontrado nesta categoria</p>
          ) : (
            items.map((item) => (
              <Link
                key={item.id}
                href={`/items/${item.id}`}
                className="block bg-white rounded-lg shadow p-6 hover:shadow-md transition"
              >
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className="font-semibold text-lg mb-2">
                      {item.description_original}
                    </h3>
                    <p className="text-sm text-gray-600 mb-2">
                      {item.explanation}
                    </p>
                    <p className="text-xs text-gray-500">
                      Página {item.page_number} • {item.unit}
                    </p>
                  </div>
                  <div className="text-right ml-4">
                    <p className="text-xl font-bold">
                      {formatCurrency(item.value, item.unit)}
                    </p>
                  </div>
                </div>
              </Link>
            ))
          )}
        </div>
      </div>
    </div>
  )
}


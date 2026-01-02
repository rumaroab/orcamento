'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'

interface Document {
  id: string
  year: number
  filename: string
  uploaded_at: string
  archived: boolean
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000'

export default function Home() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [year, setYear] = useState(new Date().getFullYear())

  useEffect(() => {
    fetchDocuments()
  }, [])

  const fetchDocuments = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/documents`)
      const data = await res.json()
      setDocuments(data)
    } catch (error) {
      console.error('Error fetching documents:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    const file = formData.get('file') as File
    
    if (!file) return

    setUploading(true)
    try {
      const uploadFormData = new FormData()
      uploadFormData.append('file', file)
      uploadFormData.append('year', year.toString())

      const res = await fetch(`${API_BASE}/api/documents/upload`, {
        method: 'POST',
        body: uploadFormData,
      })

      if (res.ok) {
        alert('Documento carregado! O processamento começará em segundo plano.')
        fetchDocuments()
      } else {
        alert('Falha no carregamento')
      }
    } catch (error) {
      console.error('Upload error:', error)
      alert('Falha no carregamento')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="min-h-screen p-8">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-4xl font-bold mb-8">Explorador de Orçamentos</h1>
        <p className="text-gray-600 mb-8">
          Carregue e explore documentos orçamentais do governo
        </p>

        {/* Upload Form */}
        <div className="bg-white rounded-lg shadow p-6 mb-8">
          <h2 className="text-2xl font-semibold mb-4">Carregar Documento Orçamental</h2>
          <form onSubmit={handleUpload} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Ano</label>
              <input
                type="number"
                value={year}
                onChange={(e) => setYear(parseInt(e.target.value))}
                className="w-full px-4 py-2 border rounded-md"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-2">Ficheiro PDF</label>
              <input
                type="file"
                name="file"
                accept=".pdf"
                className="w-full px-4 py-2 border rounded-md"
                required
              />
            </div>
            <button
              type="submit"
              disabled={uploading}
              className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {uploading ? 'A carregar...' : 'Carregar'}
            </button>
          </form>
        </div>

        {/* Documents List */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-2xl font-semibold mb-4">Documentos</h2>
          {loading ? (
            <p>A carregar...</p>
          ) : documents.length === 0 ? (
            <p className="text-gray-500">Ainda não foram carregados documentos</p>
          ) : (
            <div className="space-y-2">
              {documents.map((doc) => (
                <Link
                  key={doc.id}
                  href={`/documents/${doc.id}`}
                  className="block p-4 border rounded-md hover:bg-gray-50"
                >
                  <div className="flex justify-between items-center">
                    <div>
                      <h3 className="font-semibold">{doc.filename}</h3>
                      <p className="text-sm text-gray-500">
                        Ano: {doc.year} • Carregado: {new Date(doc.uploaded_at).toLocaleDateString('pt-PT')}
                      </p>
                    </div>
                    <span className="text-blue-600">Ver →</span>
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


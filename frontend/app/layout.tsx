import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Explorador de Orçamentos',
  description: 'Compreenda os orçamentos do governo facilmente',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="pt">
      <body>{children}</body>
    </html>
  )
}


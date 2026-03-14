import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'SharpEdge',
  description: 'Surface high-alpha betting edges before anyone else sees them',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  )
}

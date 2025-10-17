import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import HealthBadge from "@/components/health-badge"

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'LSC Blog Generator',
  description: '법무법인 블로그 자동 생성 시스템',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="ko">
      <body className={inter.className}>
        <div className="min-h-screen bg-gray-50">
          <header className="bg-white shadow-sm border-b">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
              <div className="flex justify-between items-center h-16">
                <div className="flex items-center gap-4">
                  <h1 className="text-xl font-semibold text-gray-900">
                    LSC Blog Generator
                  </h1>
                  <HealthBadge />
                </div>
                <nav className="flex space-x-8">
                  <a href="/" className="text-gray-600 hover:text-gray-900">
                    홈
                  </a>
                  <a href="/wizard" className="text-blue-600 hover:text-blue-700 font-medium">
                    마법사
                  </a>
                  <a href="/crawl" className="text-gray-600 hover:text-gray-900">
                    크롤링
                  </a>
                  <a href="/search" className="text-gray-600 hover:text-gray-900">
                    검색
                  </a>
                  <a href="/generate" className="text-gray-600 hover:text-gray-900">
                    생성
                  </a>
                  <a href="/dashboard" className="text-gray-600 hover:text-gray-900">
                    대시보드
                  </a>
                  <a href="/ops" className="text-gray-600 hover:text-gray-900">
                    운영
                  </a>
                </nav>
              </div>
            </div>
          </header>
          <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}



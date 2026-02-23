"use client"

import { Inter } from 'next/font/google'
import './globals.css'
import { Navbar } from '@/components/ui/navbar'
import { Sidebar } from '@/components/ui/sidebar'
import { useState } from 'react'

const inter = Inter({ subsets: ['latin'] })

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <html lang="en" className={inter.className}>
      <body className="bg-background text-foreground">
        <div className="flex h-screen bg-background">
          {/* Sidebar */}
          <Sidebar
            open={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
          />

          <div className="flex-1 flex flex-col">
            {/* Navbar */}
            <Navbar
              onMenuClick={() => setSidebarOpen(!sidebarOpen)}
            />

            {/* Main Content */}
            <main className="flex-1 overflow-auto">
              {children}
            </main>

            {/* Footer */}
            <footer className="border-t border-border bg-card">
              <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                <div className="py-4 text-sm text-muted-foreground">
                  © 2026 AI Agent Orchestration Platform. All rights reserved.
                </div>
              </div>
            </footer>
          </div>
        </div>
      </body>
    </html>
  )
}
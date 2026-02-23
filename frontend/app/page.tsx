'use client'

import { useState, useEffect } from 'react'
import { Navbar } from '@/components/Navbar'
import { Sidebar } from '@/components/Sidebar'
import { MainContent } from '@/components/MainContent'
import { Footer } from '@/components/Footer'
import { useAuth } from '@/hooks/useAuth'

export default function Home() {
  const { user, isAuthenticated, isLoading } = useAuth()
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)

  useEffect(() => {
    if (window.innerWidth > 1024) {
      setIsSidebarOpen(true)
    }
  }, [])

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <div className="animate-spin rounded-full h-32 w-32 border-b-2 border-primary-500"></div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Navbar
        user={user}
        isAuthenticated={isAuthenticated}
        onToggleSidebar={() => setIsSidebarOpen(!isSidebarOpen)}
      />

      <div className="flex flex-1">
        <Sidebar
          isOpen={isSidebarOpen}
          onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
          user={user}
        />
        <MainContent isSidebarOpen={isSidebarOpen}>
          <div className="p-6 space-y-6">
            <h1 className="text-3xl font-bold text-gray-900">
              AI Agent Orchestration Platform
            </h1>
            <div className="bg-white rounded-lg shadow-sm p-6">
              <h2 className="text-xl font-semibold mb-4 text-gray-700">
                Welcome to the Platform
              </h2>
              <p className="text-gray-600">
                Manage and orchestrate AI agents with ease.
                {isAuthenticated ? 'You are logged in as ' + user?.email : 'Please log in to get started.'}
              </p>
              {isAuthenticated && (
                <div className="mt-4 space-y-2">
                  <a
                    href="/workflow/new"
                    className="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-md hover:bg-primary-700 transition-colors"
                  >
                    Create New Workflow
                  </a>
                </div>
              )}
            </div>
          </div>
        </MainContent>
      </div>

      <Footer />
    </div>
  )
}
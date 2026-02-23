'use client'

import { useState, useEffect } from 'react'
import { X } from 'lucide-react'
import { Button } from './Button'
import { useRouter } from 'next/navigation'
import { User } from './Sidebar'

interface NavbarProps {
  user?: User
  isAuthenticated: boolean
  onToggleSidebar: () => void
}

interface User {
  id: string
  email: string
  name: string
  role: string
}

export const Navbar = ({ user, isAuthenticated, onToggleSidebar }: NavbarProps) => {
  const { theme, toggleTheme } = useTheme()
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  const router = useRouter()

  const handleLogout = async () => {
    const { authService } = await import('@/lib/auth')
    await authService.logout()
    router.push('/login')
  }

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo and Mobile Menu Button */}
          <div className="flex items-center">
            <button
              onClick={onToggleSidebar}
              className="lg:hidden p-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              <X className="h-6 w-6" />
            </button>
            <div className="ml-2 lg:ml-0">
              <a href="/" className="flex items-center space-x-2">
                <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-sm">A</span>
                </div>
                <span className="text-xl font-bold text-gray-900">AI Agent</span>
                <span className="text-lg text-gray-600">Orchestration</span>
              </a>
            </div>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden lg:flex items-center space-x-4">
            {isAuthenticated && (
              <div className="flex items-center space-x-4">
                <span className="text-gray-600 font-medium">
                  {user?.email}
                </span>
                <Button variant="outline" size="sm" onClick={handleLogout}>
                  Logout
                </Button>
              </div>
            )}

            <button
              onClick={toggleTheme}
              className="p-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              {theme === 'dark' ? '☀️' : '🌙'}
            </button>

            {/* Admin-only Workflow Builder Link */}
            {isAuthenticated && user?.role === 'admin' && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => router.push('/workflow/new')}
                className="bg-white hover:bg-gray-50"
              >
                Workflow Builder
              </Button>
            )}
          </div>

          {/* Mobile Menu */}
          <div className="lg:hidden">
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className="p-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              {isMobileMenuOpen ? '✕' : '☰'}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {isMobileMenuOpen && (
        <div className="absolute top-16 left-0 right-0 bg-white border-t border-gray-200">
          <div className="px-4 py-3 space-y-2">
            {isAuthenticated && (
              <div className="flex items-center justify-between">
                <span className="text-gray-600 font-medium">
                  {user?.email}
                </span>
                <Button size="sm" onClick={handleLogout}>
                  Logout
                </Button>
              </div>
            )}
            <button
              onClick={toggleTheme}
              className="w-full text-left p-2 text-gray-600 hover:bg-gray-100 rounded-md transition-colors"
            >
              {theme === 'dark' ? 'Light Mode' : 'Dark Mode'}
            </button>
          </div>
        </div>
      )}
    </nav>
  )
}
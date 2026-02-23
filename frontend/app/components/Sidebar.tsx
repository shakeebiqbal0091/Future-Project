'use client'

import { useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { User } from './Navbar'

interface SidebarProps {
  isOpen: boolean
  onToggle: () => void
  user?: User
}

export const Sidebar = ({ isOpen, onToggle }: SidebarProps) => {
  const router = useRouter()
  const [selectedItem, setSelectedItem] = useState('dashboard')

  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊', href: '/dashboard' },
    { id: 'agents', label: 'Agents', icon: '🤖', href: '/agents' },
    { id: 'workflows', label: 'Workflows', icon: '⚙️', href: '/workflows' },
    { id: 'workflow-builder', label: 'Workflow Builder', icon: '🔧', href: '/workflow/new' },
    { id: 'analytics', label: 'Analytics', icon: '📈', href: '/analytics' },
    { id: 'settings', label: 'Settings', icon: '⚙️', href: '/settings' },
  ]

  return (
    <div className={`fixed inset-0 z-40 lg:static lg:inset-0 lg:z-auto lg:overflow-y-visible lg:flex lg:flex-col lg:w-64 transition-all duration-300 ease-in-out ${isOpen ? 'translate-x-0' : '-translate-x-full'}`}>
      <div className="h-full w-full lg:static lg:inset-0 lg:overflow-y-auto lg:h-auto lg:flex lg:flex-col">
        {/* Desktop sidebar */}
        <div className="lg:flex lg:flex-col lg:fixed lg:inset-0 lg:w-64 lg:space-y-4">
          <div className="flex items-center justify-between p-6 bg-white border-b border-gray-200 lg:border-0">
            <div>
              <h2 className="text-xl font-bold text-gray-900">AI Agent</h2>
              <p className="text-sm text-gray-600">Orchestration</p>
            </div>
            <button
              onClick={onToggle}
              className="lg:hidden p-2 text-gray-600 hover:text-gray-900 transition-colors"
            >
              {isOpen ? <ChevronLeft className="h-6 w-6" /> : <ChevronRight className="h-6 w-6" />}
            </button>
          </div>

          <nav className="flex-1 px-6 py-4 space-y-2 overflow-y-auto">
            {menuItems.map((item) => {
              if (item.id === 'workflow-builder' && (!user || user.role !== 'admin')) {
                return null;
              }
              return (
                <button
                  key={item.id}
                  onClick={() => {
                    router.push(item.href)
                    setSelectedItem(item.id)
                  }}
                  className={`w-full flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors ${
                    selectedItem === item.id
                      ? 'bg-primary-50 text-primary-600'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`}
                >
                  <span className="mr-3">{item.icon}</span>
                  {item.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* Mobile sidebar backdrop */}
        {!isOpen && (
          <div className="lg:hidden fixed inset-0 bg-black bg-opacity-50 z-40"></div>
        )}
      </div>
    </div>
  )
}
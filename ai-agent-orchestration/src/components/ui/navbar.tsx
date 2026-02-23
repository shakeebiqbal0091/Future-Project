"use client"

import { useState } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { Button } from './button'
import { Badge } from './badge'
import { Avatar } from './avatar'
import { Search } from 'lucide-react'

export function Navbar({ onMenuClick }: { onMenuClick: () => void }) {
  const { user, logout } = useAuth()
  const [searchTerm, setSearchTerm] = useState('')

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    // TODO: Implement search functionality
    console.log('Search for:', searchTerm)
  }

  return (
    <nav className="border-b bg-card">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          {/* Menu Button */}
          <button
            onClick={onMenuClick}
            className="text-muted-foreground hover:text-foreground p-2 rounded-md transition-colors md:hidden"
          >
            <svg
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h16"
              />
            </svg>
          </button>

          {/* Logo */}
          <div className="flex items-center space-x-2">
            <svg
              className="h-8 w-8 text-primary"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
            >
              <path
                d="M12 2L2 7L12 12L22 7L12 2Z"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M2 17L12 22L22 17"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <path
                d="M2 12L12 17L22 12"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <span className="text-xl font-semibold text-primary">AI Agent</span>
            <span className="text-sm font-medium text-muted-foreground">Orchestrator</span>
          </div>

          {/* Search */}
          <form
            onSubmit={handleSearch}
            className="hidden md:flex items-center space-x-2 px-2 py-1 rounded-full bg-muted"
          >
            <Search className="h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search agents, workflows, tasks..."
              className="bg-transparent text-sm text-foreground placeholder-muted-foreground border-0 w-full"
            />
          </form>

          {/* User Menu */}
          <div className="flex items-center space-x-4">
            {/* Notifications */}
            <button
              className="relative text-muted-foreground hover:text-foreground p-2 rounded-md transition-colors"
            >
              <svg
                className="h-6 w-6"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                />
              </svg>
              <Badge className="absolute -top-1 -right-1" color="destructive">
                3
              </Badge>
            </button>

            {/* User Avatar */}
            {user && (
              <div className="relative">
                <Avatar className="cursor-pointer" size="sm" />
                <div className="absolute -bottom-0.5 -right-0.5 bg-primary rounded-full w-1.5 h-1.5"></div>
              </div>
            )}

            {/* User Menu */}
            <div className="hidden lg:block">
              {user ? (
                <>
                  <span className="text-sm font-medium text-foreground">
                    {user.name}
                  </span>
                  <button
                    onClick={logout}
                    className="ml-2 text-sm text-muted-foreground hover:text-destructive transition-colors"
                  >
                    Logout
                  </button>
                </>
              ) : (
                <>
                  <Button size="sm" variant="outline" asChild>
                    <a href="/login">Login</a>
                  </Button>
                  <Button size="sm" asChild>
                    <a href="/register">Sign Up</a>
                  </Button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </nav>
  )
}
"use client"

import { useState } from 'react'
import { Button } from './button'
import { SidebarContent } from './sidebar-content'

interface SidebarProps {
  open: boolean
  onClose: () => void
}

export function Sidebar({ open, onClose }: SidebarProps) {
  const [activeItem, setActiveItem] = useState('dashboard')

  return (
    <div className={`fixed inset-0 z-50 flex md:hidden ${open ? 'visible' : 'invisible'} transition-all duration-300`}>
      <div
        onClick={onClose}
        className={`fixed inset-0 bg-black bg-opacity-50 transition-opacity duration-300 ${open ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
      />

      <div className={`relative flex-1 flex flex-col max-w-xs w-80 bg-card transition-all duration-300 ease-in-out ${open ? 'translate-x-0' : '-translate-x-full'}`}>
        {/* Close Button */}
        <div className="flex h-16 items-center justify-between px-4 border-b border-border">
          <h2 className="text-lg font-semibold text-foreground">AI Agent Orchestrator</h2>
          <Button variant="ghost" size="sm" onClick={onClose}>
            ×
          </Button>
        </div>

        {/* Sidebar Content */}
        <div className="flex-1 overflow-y-auto">
          <SidebarContent activeItem={activeItem} onItemSelect={setActiveItem} />
        </div>

        {/* User Info */}
        <div className="px-4 py-3 border-t border-border">
          <div className="flex items-center space-x-3">
            <div className="relative">
              <div className="w-8 h-8 rounded-full bg-primary"></div>
              <div className="absolute -bottom-0.5 -right-0.5 bg-green-500 rounded-full w-2 h-2"></div>
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">Admin User</p>
              <p className="text-xs text-muted-foreground">admin@example.com</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
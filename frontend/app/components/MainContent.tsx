'use client'

import { ReactNode } from 'react'

interface MainContentProps {
  children: ReactNode
  isSidebarOpen?: boolean
}

export const MainContent = ({ children, isSidebarOpen = true }: MainContentProps) => {
  return (
    <main className={`flex-1 overflow-x-hidden transition-all duration-300 ease-in-out ${!isSidebarOpen ? 'ml-0' : 'ml-64'}`}>
      <div className="relative z-0 flex-1 p-6 sm:px-6">
        {children}
      </div>
    </main>
  )
}
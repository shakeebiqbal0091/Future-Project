'use client'

import { ReactNode } from 'react'

export const Footer = ({ children }: { children?: ReactNode }) => {
  return (
    <footer className="bg-white border-t border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
        <p className="text-sm text-gray-600 text-center">
          © 2026 AI Agent Orchestration Platform. All rights reserved.
        </p>
      </div>
    </footer>
  )
}
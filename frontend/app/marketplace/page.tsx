'use client'

import { useState, useEffect } from 'react'
import { useAuth } from '@/hooks/useAuth'
import { api } from '@/lib/api'
import { Button } from '@/components/Button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/Card'
import { Input } from '@/components/Input'
import { Select } from '@/components/Select'
import { LoadingSpinner } from '@/components/LoadingSpinner'
import { Alert, AlertDescription, AlertIcon } from '@/components/Alert'
import { MarketplaceGrid } from '@/components/marketplace/MarketplaceGrid'
import { SearchFilter } from '@/components/marketplace/SearchFilter'
import { CategoryFilter } from '@/components/marketplace/CategoryFilter'
import { PriceFilter } from '@/components/marketplace/PriceFilter'
import { Pagination } from '@/components/Pagination'

export default function Marketplace() {
  const { user, isAuthenticated } = useAuth()
  const [agents, setAgents] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [searchTerm, setSearchTerm] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('all')
  const [selectedPriceRange, setSelectedPriceRange] = useState('all')
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [isInstalling, setIsInstalling] = useState(null)

  const fetchAgents = async (page = 1) => {
    try {
      setLoading(true)
      setError('')

      const response = await api.get('/api/v1/marketplace/agents', {
        params: {
          page,
          search: searchTerm,
          category: selectedCategory === 'all' ? undefined : selectedCategory,
          price: selectedPriceRange === 'all' ? undefined : selectedPriceRange,
        },
      })

      setAgents(response.data.agents)
      setTotalPages(response.data.totalPages)
      setCurrentPage(page)
    } catch (err) {
      setError('Failed to load agents. Please try again.')
      console.error('Error fetching agents:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAgents()
  }, [searchTerm, selectedCategory, selectedPriceRange, currentPage])

  const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchTerm(e.target.value)
    setCurrentPage(1)
  }

  const handleCategoryChange = (category: string) => {
    setSelectedCategory(category)
    setCurrentPage(1)
  }

  const handlePriceChange = (priceRange: string) => {
    setSelectedPriceRange(priceRange)
    setCurrentPage(1)
  }

  const handleInstall = async (agentId: string) => {
    if (!isAuthenticated) {
      window.location.href = '/login'
      return
    }

    setIsInstalling(agentId)

    try {
      await api.post(`/api/v1/marketplace/agents/${agentId}/install`)

      // Refresh agents list to show updated status
      await fetchAgents(currentPage)

      // Show success notification (would be implemented with toast)
      console.log('Agent installed successfully')
    } catch (err) {
      console.error('Error installing agent:', err)
      // Show error notification
    } finally {
      setIsInstalling(null)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          <LoadingSpinner />
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 p-6">
        <div className="max-w-7xl mx-auto">
          <Alert variant="destructive">
            <AlertIcon />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Agent Marketplace</h1>
          <p className="mt-2 text-gray-600">
            Browse pre-built AI agents from our community. Find agents for sales, support, operations, and more.
          </p>
        </div>

        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="text-lg">Filters</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <SearchFilter value={searchTerm} onChange={handleSearch} />
            <CategoryFilter
              selectedCategory={selectedCategory}
              onCategoryChange={handleCategoryChange}
            />
            <PriceFilter
              selectedPriceRange={selectedPriceRange}
              onPriceChange={handlePriceChange}
            />
          </CardContent>
        </Card>

        <MarketplaceGrid
          agents={agents}
          isInstalling={isInstalling}
          onInstall={handleInstall}
        />

        {totalPages > 1 && (
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={setCurrentPage}
          />
        )}
      </div>
    </div>
  )
}
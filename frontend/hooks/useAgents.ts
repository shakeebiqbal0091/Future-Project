import { useState, useEffect } from 'react'
import { useAuth } from './useAuth'
import { api } from '../lib/api'

interface Agent {
  id: string
  name: string
  description: string
  category: string
  price: number
  rating: number
  reviews: number
  image_url?: string
  is_installed: boolean
  created_by: {
    name: string
    avatar_url?: string
  }
  featured: boolean
}

interface UseAgentsState {
  agents: Agent[]
  featuredAgents: Agent[]
  loading: boolean
  error: string | null
  searchQuery: string
  setSearchQuery: (query: string) => void
  selectedCategory: string | null
  setSelectedCategory: (category: string | null) => void
  sortOption: 'relevance' | 'price-low' | 'price-high' | 'rating'
  setSortOption: (option: 'relevance' | 'price-low' | 'price-high' | 'rating') => void
  currentPage: number
  setCurrentPage: (page: number) => void
  totalPages: number
  fetchAgents: () => void
}

export function useAgents(): UseAgentsState {
  const { isAuthenticated } = useAuth()
  const [agents, setAgents] = useState<Agent[]>([])
  const [featuredAgents, setFeaturedAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [sortOption, setSortOption] = useState<'relevance' | 'price-low' | 'price-high' | 'rating'>('relevance')
  const [currentPage, setCurrentPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

  const fetchAgents = async () => {
    try {
      setLoading(true)
      setError(null)

      const params: Record<string, any> = {
        page: currentPage,
        search: searchQuery.trim() || undefined,
        category: selectedCategory || undefined,
        sort: sortOption,
      }

      const response = await api.get('/api/v1/marketplace/agents', { params })

      setAgents(response.data.agents)
      setFeaturedAgents(response.data.featured_agents || [])
      setTotalPages(response.data.total_pages || 1)
    } catch (err: any) {
      setError('Failed to load agents. Please try again later.')
      console.error('Error fetching agents:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleInstall = async (agentId: string) => {
    if (!isAuthenticated) {
      window.location.href = '/login'
      return
    }

    try {
      await api.post(`/api/v1/marketplace/agents/${agentId}/install`)

      // Refresh agents list to show updated status
      await fetchAgents()

      // Show success notification (would be implemented with toast)
      console.log('Agent installed successfully')
    } catch (err: any) {
      console.error('Error installing agent:', err)
      // Show error notification
    }
  }

  useEffect(() => {
    fetchAgents()
  }, [searchQuery, selectedCategory, sortOption, currentPage])

  return {
    agents,
    featuredAgents,
    loading,
    error,
    searchQuery,
    setSearchQuery,
    selectedCategory,
    setSelectedCategory,
    sortOption,
    setSortOption,
    currentPage,
    setCurrentPage,
    totalPages,
    fetchAgents,
    handleInstall
  }
}
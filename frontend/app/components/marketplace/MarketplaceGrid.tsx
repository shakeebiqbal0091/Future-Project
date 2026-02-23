'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle, CardStatus } from '@/components/Card'
import { Button } from '@/components/Button'
import { StarIcon } from '@/components/icons/StarIcon'
import { ClockIcon } from '@/components/icons/ClockIcon'
import { ShieldCheckIcon } from '@/components/icons/ShieldCheckIcon'
import { PriceTagIcon } from '@/components/icons/PriceTagIcon'
import { UsersIcon } from '@/components/icons/UsersIcon'
import { TagIcon } from '@/components/icons/TagIcon'
import { CheckCircleIcon } from '@/components/icons/CheckCircleIcon'
import { XCircleIcon } from '@/components/icons/XCircleIcon'
import { ExternalLinkIcon } from '@/components/icons/ExternalLinkIcon'
import { formatCurrency, formatDateTime } from '@/lib/utils'

interface Agent {
  id: string
  name: string
  description: string
  category: string
  price: number
  rating: number
  reviews: number
  author: string
  created_at: string
  version: string
  compatible: boolean
  installed: boolean
  tools: string[]
  requirements: string[]
}

interface MarketplaceGridProps {
  agents: Agent[]
  isInstalling: string | null
  onInstall: (agentId: string) => void
}

export function MarketplaceGrid({ agents, isInstalling, onInstall }: MarketplaceGridProps) {
  if (agents.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm p-8 text-center">
        <div className="text-gray-500 text-xl mb-4">📦</div>
        <h3 className="text-gray-900 font-semibold mb-2">No agents found</h3>
        <p className="text-gray-600 mb-6">
          Try adjusting your filters or search terms.
        </p>
        <div className="grid grid-cols-2 gap-2 max-w-md mx-auto">
          <Button variant="outline" onClick={() => window.location.reload()}>
            Reset Filters
          </Button>
          <Button onClick={() => window.location.href = '/submit-agent'}>
            Submit Your Agent
          </Button>
        </div>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {agents.map((agent) => (
        <AgentCard
          key={agent.id}
          agent={agent}
          isInstalling={isInstalling === agent.id}
          onInstall={onInstall}
        />
      ))}
    </div>
  )
}

interface AgentCardProps {
  agent: Agent
  isInstalling: boolean
  onInstall: (agentId: string) => void
}

function AgentCard({ agent, isInstalling, onInstall }: AgentCardProps) {
  const handleInstallClick = () => {
    onInstall(agent.id)
  }

  const getInstallButton = () => {
    if (agent.installed) {
      return (
        <Button variant="success" size="sm" disabled>
          <CheckCircleIcon className="w-4 h-4 mr-2" />
          Installed
        </Button>
      )
    }

    if (isInstalling) {
      return (
        <Button variant="primary" size="sm" disabled>
          <ClockIcon className="w-4 h-4 mr-2" />
          Installing...
        </Button>
      )
    }

    if (!agent.compatible) {
      return (
        <Button variant="destructive" size="sm" disabled>
          <XCircleIcon className="w-4 h-4 mr-2" />
          Not Compatible
        </Button>
      )
    }

    return (
      <Button variant="primary" size="sm" onClick={handleInstallClick}>
        <PriceTagIcon className="w-4 h-4 mr-2" />
        Install
      </Button>
    )
  }

  return (
    <Card className="hover:shadow-lg transition-shadow">
      <CardHeader className="pb-4">
        <div className="flex justify-between items-start mb-2">
          <CardTitle className="text-lg">{agent.name}</CardTitle>
          <div className="flex items-center space-x-2">
            <StarIcon className="w-4 h-4 text-yellow-400" />
            <span className="text-sm font-medium text-gray-700">{agent.rating}</span>
            <span className="text-sm text-gray-400">({agent.reviews})</span>
          </div>
        </div>
        <CardDescription className="text-sm text-gray-600 mb-3">
          {agent.description}
        </CardDescription>
        <div className="flex items-center space-x-4 text-sm text-gray-500">
          <div className="flex items-center space-x-1">
            <TagIcon className="w-4 h-4 text-gray-400" />
            <span className="capitalize">{agent.category}</span>
          </div>
          <div className="flex items-center space-x-1">
            <PriceTagIcon className="w-4 h-4 text-gray-400" />
            {formatCurrency(agent.price)}
          </div>
          <div className="flex items-center space-x-1">
            <UsersIcon className="w-4 h-4 text-gray-400" />
            {agent.author}
          </div>
          <div className="flex items-center space-x-1">
            <ClockIcon className="w-4 h-4 text-gray-400" />
            {formatDateTime(agent.created_at)}
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-4 border-t">
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-1">
              <CheckCircleIcon className="w-4 h-4 text-green-500" />
              <span className="text-sm font-medium text-gray-900">
                Version {agent.version}
              </span>
            </div>
            <div className="text-xs text-gray-500">
              Latest stable version
            </div>
          </div>
          <div className="space-y-1">
            <div className="flex items-center space-x-1">
              <ShieldCheckIcon className="w-4 h-4 text-blue-500" />
              <span className="text-sm font-medium text-gray-900">
                {agent.compatible ? 'Compatible' : 'Incompatible'}
              </span>
            </div>
            <div className="text-xs text-gray-500">
              Platform requirements met
            </div>
          </div>
        </div>
        <div className="mb-4">
          <h4 className="text-sm font-semibold text-gray-900 mb-2">Tools Included</h4>
          <div className="flex flex-wrap gap-2">
            {agent.tools.slice(0, 4).map((tool, index) => (
              <span
                key={index}
                className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded-full"
              >
                {tool}
              </span>
            ))}
            {agent.tools.length > 4 && (
              <span className="px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded-full">
                +{agent.tools.length - 4} more
              </span>
            )}
          </div>
        </div>
        <div className="space-y-2">
          <h4 className="text-sm font-semibold text-gray-900 mb-2">Requirements</h4>
          <div className="text-xs text-gray-500 space-y-1">
            {agent.requirements.map((req, index) => (
              <div key={index}>• {req}</div>
            ))}
          </div>
        </div>
        <div className="mt-4 pt-4 border-t flex justify-between items-center">
          <div className="space-y-1">
            <div className="text-sm text-gray-500">By {agent.author}</div>
            <div className="text-xs text-gray-400">
              {formatDateTime(agent.created_at)}
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {getInstallButton()}
            <button
              onClick={(e) => {
                e.stopPropagation()
                window.open(`/marketplace/${agent.id}`, '_blank')
              }}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <ExternalLinkIcon className="w-4 h-4" />
            </button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
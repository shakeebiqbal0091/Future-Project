"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Badge } from './ui/badge'
import { Skeleton } from './ui/skeleton'
import { AgentForm } from './agent-form'
import { useRouter } from 'next/navigation'

interface AgentCardProps {
  agent: Agent
  onEdit: (agent: Agent) => void
  onDelete: (agentId: string) => void
}

interface Agent {
  id: string
  name: string
  role: string
  status: string
  model: string
  tools: string[]
  created_at: string
  updated_at: string
}

const STATUS_COLORS = {
  active: 'green',
  inactive: 'gray',
  archived: 'red',
}

export function AgentManagement() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const router = useRouter()

  useEffect(() => {
    fetchAgents()
  }, [])

  const fetchAgents = async () => {
    try {
      // Mock API call - replace with real API
      const response = await new Promise<Agent[]>((resolve) => {
        setTimeout(() => {
          resolve([
            {
              id: '1',
              name: 'Sales Assistant',
              role: 'Customer Support',
              status: 'active',
              model: 'claude-sonnet-4',
              tools: ['calculator', 'http_request'],
              created_at: '2024-01-15T10:00:00Z',
              updated_at: '2024-01-20T14:30:00Z'
            },
            {
              id: '2',
              name: 'Email Bot',
              role: 'Email Automation',
              status: 'inactive',
              model: 'claude-haiku-4',
              tools: ['email_send'],
              created_at: '2024-01-18T09:15:00Z',
              updated_at: '2024-01-18T09:15:00Z'
            },
            {
              id: '3',
              name: 'Data Processor',
              role: 'Data Analysis',
              status: 'active',
              model: 'claude-opus-4',
              tools: ['http_request'],
              created_at: '2024-01-22T16:45:00Z',
              updated_at: '2024-01-22T16:45:00Z'
            }
          ])
        }, 500)
      })
      setAgents(response)
    } catch (error) {
      console.error('Error fetching agents:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateAgent = (agent: Agent) => {
    // Mock API call to create agent
    console.log('Creating agent:', agent)
    setShowForm(false)
    fetchAgents()
  }

  const handleEditAgent = (agent: Agent) => {
    console.log('Editing agent:', agent)
    router.push(`/agents/${agent.id}`)
  }

  const handleDeleteAgent = (agentId: string) => {
    if (confirm('Are you sure you want to delete this agent?')) {
      // Mock API call to delete agent
      console.log('Deleting agent:', agentId)
      setAgents(agents.filter(agent => agent.id !== agentId))
    }
  }

  const getStatusColor = (status: string) => STATUS_COLORS[status as keyof typeof STATUS_COLORS] || 'gray'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-foreground">Agent Management</h1>
        <Button
          onClick={() => setShowForm(true)}
          variant="default"
          className="bg-primary text-primary-foreground hover:bg-primary/90"
        >
          + Create Agent
        </Button>
      </div>

      {/* Agent Form Modal */}
      {showForm && (
        <AgentForm
          onSubmit={handleCreateAgent}
          onClose={() => setShowForm(false)}
        />
      )}

      {/* Agents Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(3)].map((_, i) => (
            <Card key={i} className="p-4">
              <Skeleton className="w-full h-8 mb-3" />
              <Skeleton className="w-full h-6 mb-2" />
              <Skeleton className="w-1/2 h-4" />
            </Card>
          ))}
        </div>
      ) : agents.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map(agent => (
            <AgentCard
              key={agent.id}
              agent={agent}
              onEdit={handleEditAgent}
              onDelete={handleDeleteAgent}
            />
          ))}
        </div>
      ) : (
        <Card className="text-center p-8">
          <CardTitle>No agents created yet</CardTitle>
          <CardDescription>
            Create your first AI agent to get started
          </CardDescription>
        </Card>
      )}
    </div>
  )
}

function AgentCard({ agent, onEdit, onDelete }: AgentCardProps) {
  const getStatusColor = (status: string) => STATUS_COLORS[status as keyof typeof STATUS_COLORS] || 'gray'

  return (
    <Card className="relative">
      {/* Status Badge */}
      <Badge
        variant="secondary"
        className={`absolute top-3 right-3 bg-${getStatusColor(agent.status)}-100 text-${getStatusColor(agent.status)}-800`}
      >
        {agent.status}
      </Badge>

      <CardContent className="p-6">
        {/* Header */}
        <div className="flex justify-between items-start mb-4">
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-foreground mb-1">{agent.name}</h3>
            <p className="text-sm text-muted-foreground">{agent.role}</p>
          </div>
          <div className="flex space-x-2">
            <Badge variant="secondary" className="bg-blue-100 text-blue-800">{agent.model}</Badge>
          </div>
        </div>

        {/* Tools */}
        <div className="flex flex-wrap gap-2 mb-4">
          {agent.tools.map(tool => (
            <Badge key={tool} variant="secondary" className="bg-purple-100 text-purple-800">
              {tool}
            </Badge>
          ))}
        </div>

        {/* Meta Info */}
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <div>
            Created: {new Date(agent.created_at).toLocaleDateString()}
          </div>
          <div>
            Updated: {new Date(agent.updated_at).toLocaleDateString()}
          </div>
        </div>

        {/* Actions */}
        <div className="mt-4 pt-4 border-t border-border flex space-x-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onEdit(agent)}
            className="text-blue-600 hover:bg-blue-50"
          >
            Edit
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => onDelete(agent.id)}
            className="text-red-600 hover:bg-red-50"
          >
            Delete
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => {}}
            className="text-green-600 hover:bg-green-50"
          >
            Test
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
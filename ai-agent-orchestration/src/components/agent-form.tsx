"use client"

import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Select } from './ui/select'
import { Switch } from './ui/switch'
import { CodeEditor } from '../ui/code-editor'
import { Badge } from './ui/badge'

interface AgentFormProps {
  onSubmit: (agent: Agent) => void
}

interface Agent {
  id?: string
  name: string
  role: string
  instructions: string
  model: string
  tools: string[]
}

const MODELS = [
  { value: 'claude-sonnet-4', label: 'Claude Sonnet 4' },
  { value: 'claude-opus-4', label: 'Claude Opus 4' },
  { value: 'claude-haiku-4', label: 'Claude Haiku 4' },
]

const TOOLS = [
  { name: 'calculator', label: 'Calculator', description: 'Performs arithmetic operations' },
  { name: 'http_request', label: 'HTTP Request', description: 'Make HTTP API calls' },
  { name: 'email_send', label: 'Email Send', description: 'Send email via connected account' },
  { name: 'slack_post', label: 'Slack Post', description: 'Post message to Slack' },
]

export function AgentForm({ onSubmit }: AgentFormProps) {
  const [agent, setAgent] = useState<Agent>({
    name: '',
    role: '',
    instructions: '',
    model: 'claude-sonnet-4',
    tools: []
  })
  const [loading, setLoading] = useState(false)

  const handleCreateAgent = async () => {
    setLoading(true)
    try {
      onSubmit(agent)
    } catch (error) {
      console.error('Error creating agent:', error)
    } finally {
      setLoading(false)
    }
  }

  const toggleTool = (toolName: string) => {
    setAgent(prev => {
      const newTools = prev.tools.includes(toolName)
        ? prev.tools.filter(tool => tool !== toolName)
        : [...prev.tools, toolName]
      return { ...prev, tools: newTools }
    })
  }

  return (
    <Card className="w-full max-w-4xl">
      <CardHeader>
        <CardTitle>Create New Agent</CardTitle>
        <CardDescription>
          Build intelligent AI agents to automate your workflows
        </CardDescription>
      </CardHeader>

      <CardContent>
        {/* Agent Name and Role */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <Input
              label="Agent Name"
              placeholder="Enter agent name"
              value={agent.name}
              onChange={(e) => setAgent(prev => ({ ...prev, name: e.target.value }))}
              required
            />
          </div>

          <div>
            <Input
              label="Role"
              placeholder="e.g., Sales Assistant, Support Bot"
              value={agent.role}
              onChange={(e) => setAgent(prev => ({ ...prev, role: e.target.value }))}
              required
            />
          </div>
        </div>

        {/* System Prompt */}
        <div className="mt-4">
          <label className="block text-sm font-medium text-muted-foreground mb-2">
            System Instructions
          </label>
          <CodeEditor
            value={agent.instructions}
            onChange={(value) => setAgent(prev => ({ ...prev, instructions: value }))}
            placeholder="Define your agent's behavior, personality, and constraints..."
            language="plaintext"
            className="h-64"
          />
        </div>

        {/* Model Selection */}
        <div className="mt-4">
          <label className="block text-sm font-medium text-muted-foreground mb-2">
            Select Model
          </label>
          <Select
            value={agent.model}
            onChange={(e) => setAgent(prev => ({ ...prev, model: e.target.value }))}
            className="w-full"
          >
            {MODELS.map(model => (
              <option key={model.value} value={model.value}>
                {model.label}
              </option>
            ))}
          </Select>
        </div>

        {/* Tool Permissions */}
        <div className="mt-6">
          <h3 className="text-lg font-semibold mb-3">Tool Permissions</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {TOOLS.map(tool => (
              <div key={tool.name} className="flex items-center space-x-2">
                <Switch
                  checked={agent.tools.includes(tool.name)}
                  onChange={() => toggleTool(tool.name)}
                />
                <div className="flex-1">
                  <div className="font-medium text-foreground">{tool.label}</div>
                  <div className="text-sm text-muted-foreground">{tool.description}</div>
                </div>
                {agent.tools.includes(tool.name) && (
                  <Badge variant="default">Active</Badge>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Create Button */}
        <div className="mt-8 pt-6 border-t border-border flex justify-end space-x-3">
          <Button variant="outline" onClick={() => {}}>
            Cancel
          </Button>
          <Button
            onClick={handleCreateAgent}
            disabled={!agent.name || !agent.role || !agent.instructions}
            loading={loading}
          >
            Create Agent
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

// Mock Code Editor component for now
interface CodeEditorProps {
  value: string
  onChange: (value: string) => void
  placeholder?: string
  language?: string
  className?: string
}

export function CodeEditor({ value, onChange, placeholder, language = 'plaintext', className = '' }: CodeEditorProps) {
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className={`w-full p-3 border border-border rounded-lg bg-background text-foreground text-sm font-mono resize-none ${className}`}
      style={{ minHeight: '200px' }}
    />
  )
}
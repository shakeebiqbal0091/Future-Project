"use client"

import { useState, useEffect, useRef, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './ui/card'
import { Button } from './ui/button'
import { Input } from './ui/input'
import { Select } from './ui/select'
import { Badge } from './ui/badge'
import { Tooltip } from './ui/tooltip'
import { Dialog } from './ui/dialog'
import { useRouter } from 'next/navigation'
import { Node } from 'reactflow'

// Import React Flow
import ReactFlow, {
  Node as ReactFlowNode,
  Edge,
  addEdge,
  Connection,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
  MiniMap,
  useZoomPanHelper,
  ReactFlowProvider,
  NodeTypes,
  NodeData,
  Position,
  OnLoadParams
} from 'reactflow'

// Import custom node types
import { AgentNode } from './workflow-nodes/agent-node'
import { DecisionNode } from './workflow-nodes/decision-node'
import { ActionNode } from './workflow-nodes/action-node'
import { InputNode } from './workflow-nodes/input-node'
import { OutputNode } from './workflow-nodes/output-node'

// Export node types for external use
export const nodeTypes: NodeTypes = {
  agent: AgentNode,
  decision: DecisionNode,
  action: ActionNode,
  input: InputNode,
  output: OutputNode,
}

// Interface definitions
interface WorkflowNode extends ReactFlowNode {
  type: 'agent' | 'decision' | 'action' | 'input' | 'output'
  data: {
    id: string
    name: string
    type: string
    agentId?: string
    tool?: string
    condition?: string
    value?: string
    position: { x: number; y: number }
  }
}

interface WorkflowEdge extends Edge {
  id: string
  source: string
  target: string
  type: 'default'
  animated?: boolean
  arrowHeadType?: string
  label?: string
  labelStyle?: any
}

interface Workflow {
  id?: string
  name: string
  description: string
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  status: 'draft' | 'active' | 'archived'
}

interface Agent {
  id: string
  name: string
  role: string
  model: string
  tools: string[]
}

// Mock data for agents (replace with API calls)
const mockAgents = [
  { id: '1', name: 'Sales Assistant', role: 'Customer Support', model: 'claude-sonnet-4', tools: ['calculator', 'http_request'] },
  { id: '2', name: 'Email Bot', role: 'Email Automation', model: 'claude-haiku-4', tools: ['email_send'] },
  { id: '3', name: 'Data Processor', role: 'Data Analysis', model: 'claude-opus-4', tools: ['http_request'] },
]

// Available tools
const availableTools = [
  { name: 'calculator', label: 'Calculator', description: 'Performs arithmetic operations' },
  { name: 'http_request', label: 'HTTP Request', description: 'Make HTTP API calls' },
  { name: 'email_send', label: 'Email Send', description: 'Send email via connected account' },
  { name: 'slack_post', label: 'Slack Post', description: 'Post message to Slack' },
]

// Custom node types
interface CustomNode {
  id: string
  type: 'agent' | 'decision' | 'action' | 'input' | 'output'
  position: { x: number; y: number }
  data: {
    id: string
    name: string
    type: string
    agentId?: string
    tool?: string
    condition?: string
    value?: string
  }
}

export function WorkflowDesigner({ workflowId }: { workflowId?: string }) {
  const [workflow, setWorkflow] = useState<Workflow>({
    name: '',
    description: '',
    nodes: [],
    edges: [],
    status: 'draft'
  })
  const [selectedNode, setSelectedNode] = useState<WorkflowNode | null>(null)
  const [showPropertiesPanel, setShowPropertiesPanel] = useState(false)
  const [showNodeConfig, setShowNodeConfig] = useState<false | 'agent' | 'decision' | 'action' | 'input' | 'output'>(false)
  const [loading, setLoading] = useState(false)
  const [agents, setAgents] = useState<Agent[]>([])
  const [nodeTypesList, setNodeTypesList] = useState<string[]>(['agent', 'decision', 'action', 'input', 'output'])
  const [toolboxOpen, setToolboxOpen] = useState(false)
  const router = useRouter()

  // React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState<WorkflowNode>(workflow.nodes)
  const [edges, setEdges, onEdgesChange] = useEdgesState<WorkflowEdge>(workflow.edges)
  const [tooltippedNode, setTooltippedNode] = useState<string | null>(null)

  // Refs
  const reactFlowWrapper = useRef<HTMLDivElement>(null)
  const reactFlowInstance = useRef<OnLoadParams>(null)

  // Node positions for new nodes
  const [newNodePosition, setNewNodePosition] = useState<{ x: number; y: number }>({ x: 0, y: 0 })

  // Initialize
  useEffect(() => {
    loadWorkflow()
    loadAgents()
  }, [workflowId])

  // Load workflow data (mock for now)
  const loadWorkflow = async () => {
    if (workflowId) {
      setLoading(true)
      try {
        // Mock API call - replace with real API
        const mockWorkflow: Workflow = {
          id: workflowId,
          name: 'Content Generation Pipeline',
          description: 'Automated content creation workflow',
          nodes: [
            {
              id: '1',
              type: 'input',
              position: { x: 100, y: 100 },
              data: { id: '1', name: 'Input', type: 'input', value: 'User input' }
            },
            {
              id: '2',
              type: 'agent',
              position: { x: 400, y: 100 },
              data: { id: '2', name: 'Content Writer', type: 'agent', agentId: '1' }
            },
            {
              id: '3',
              type: 'action',
              position: { x: 700, y: 100 },
              data: { id: '3', name: 'Publish Content', type: 'action', tool: 'http_request' }
            },
            {
              id: '4',
              type: 'output',
              position: { x: 1000, y: 100 },
              data: { id: '4', name: 'Output', type: 'output', value: 'Published content' }
            }
          ],
          edges: [
            { id: 'e1-2', source: '1', target: '2' },
            { id: 'e2-3', source: '2', target: '3' },
            { id: 'e3-4', source: '3', target: '4' }
          ],
          status: 'active'
        }

        setWorkflow(mockWorkflow)
        setNodes(mockWorkflow.nodes)
        setEdges(mockWorkflow.edges)
      } catch (error) {
        console.error('Error loading workflow:', error)
      } finally {
        setLoading(false)
      }
    }
  }

  // Load agents data
  const loadAgents = async () => {
    try {
      // Mock API call - replace with real API
      setAgents(mockAgents)
    } catch (error) {
      console.error('Error loading agents:', error)
    }
  }

  // Handle node selection
  const handleNodeClick = (event: React.MouseEvent, node: WorkflowNode) => {
    event.stopPropagation()
    setSelectedNode(node)
    setShowPropertiesPanel(true)
  }

  // Handle edge connection
  const onConnect = (params: Connection) => {
    const edge = addEdge(params, edges)
    if (edge) {
      setEdges((eds) => eds.concat(edge))
    }
  }

  // Handle node delete
  const handleDeleteNode = () => {
    if (selectedNode) {
      setNodes((nds) => nds.filter((node) => node.id !== selectedNode.id))
      setEdges((eds) => eds.filter((edge) => edge.source !== selectedNode.id && edge.target !== selectedNode.id))
      setSelectedNode(null)
      setShowPropertiesPanel(false)
    }
  }

  // Handle edge delete
  const handleDeleteEdge = (edgeId: string) => {
    setEdges((eds) => eds.filter((edge) => edge.id !== edgeId))
  }

  // Handle node type change
  const handleNodeTypeChange = (newType: string) => {
    if (selectedNode) {
      // Update node type
      const newNode: WorkflowNode = {
        ...selectedNode,
        type: newType as any,
        data: {
          ...selectedNode.data,
          type: newType
        }
      }

      setNodes((nds) => nds.map((node) => (node.id === selectedNode.id ? newNode : node)))
      setSelectedNode(newNode)
    }
  }

  // Handle workflow save
  const handleSaveWorkflow = async () => {
    setLoading(true)
    try {
      const updatedWorkflow: Workflow = {
        ...workflow,
        name: workflow.name || 'Untitled Workflow',
        nodes: nodes,
        edges: edges
      }

      // Mock API call - replace with real API
      console.log('Saving workflow:', updatedWorkflow)

      // Show success message
      const savedWorkflow = { ...updatedWorkflow, id: 'saved-123' }
      setWorkflow(savedWorkflow)

      // Navigate to workflow view
      router.push(`/workflows/${savedWorkflow.id}`)
    } catch (error) {
      console.error('Error saving workflow:', error)
    } finally {
      setLoading(false)
    }
  }

  // Handle workflow validation
  const validateWorkflow = () => {
    const errors: string[] = []

    // Check for start node
    const hasStartNode = nodes.some(node => node.type === 'input')
    if (!hasStartNode) {
      errors.push('Workflow must have an input node as the starting point')
    }

    // Check for end node
    const hasEndNode = nodes.some(node => node.type === 'output')
    if (!hasEndNode) {
      errors.push('Workflow must have an output node as the ending point')
    }

    // Check for disconnected nodes
    const connectedNodeIds = new Set<string>()
    edges.forEach(edge => {
      connectedNodeIds.add(edge.source)
      connectedNodeIds.add(edge.target)
    })

    const disconnectedNodes = nodes.filter(node => !connectedNodeIds.has(node.id))
    if (disconnectedNodes.length > 0) {
      errors.push(`Found ${disconnectedNodes.length} disconnected node(s): ${disconnectedNodes.map(n => n.data.name).join(', ')}`)
    }

    // Check for loops
    // Simple cycle detection
    const adjacencyList: { [key: string]: string[] } = {}
    edges.forEach(edge => {
      if (!adjacencyList[edge.source]) {
        adjacencyList[edge.source] = []
      }
      adjacencyList[edge.source].push(edge.target)
    })

    const hasCycle = detectCycle(adjacencyList)
    if (hasCycle) {
      errors.push('Workflow contains a cycle/loop')
    }

    return errors
  }

  // Cycle detection algorithm
  const detectCycle = (graph: { [key: string]: string[] }): boolean => {
    const visited = new Set<string>()
    const recStack = new Set<string>()

    const dfs = (node: string): boolean => {
      if (!recStack.has(node)) {
        visited.add(node)
        recStack.add(node)

        for (const neighbor of graph[node] || []) {
          if (!visited.has(neighbor) && dfs(neighbor)) {
            return true
          } else if (recStack.has(neighbor)) {
            return true
          }
        }
      }
      recStack.delete(node)
      return false
    }

    for (const node in graph) {
      if (!visited.has(node) && dfs(node)) {
        return true
      }
    }

    return false
  }

  // Handle workflow run preview
  const handleRunPreview = async () => {
    const errors = validateWorkflow()
    if (errors.length > 0) {
      alert('Workflow validation errors:\n' + errors.join('\n'))
      return
    }

    setLoading(true)
    try {
      // Mock execution preview
      console.log('Running workflow preview:', {
        nodes: nodes.map(n => ({ id: n.id, type: n.type, data: n.data })),
        edges: edges
      })

      // Show preview results (mock)
      setTimeout(() => {
        alert('Workflow executed successfully!\n\nPreview results:\n- Input processed\n- Agent executed\n- Action completed\n- Output generated')
      }, 1000)
    } catch (error) {
      console.error('Error running workflow preview:', error)
      alert('Error running workflow: ' + (error as Error).message)
    } finally {
      setLoading(false)
    }
  }

  // Handle adding new node from toolbox
  const handleAddNode = (type: 'agent' | 'decision' | 'action' | 'input' | 'output') => {
    const newNode: WorkflowNode = {
      id: `node-${Date.now()}`,
      type,
      position: { x: newNodePosition.x, y: newNodePosition.y },
      data: {
        id: `node-${Date.now()}`,
        name: type.charAt(0).toUpperCase() + type.slice(1),
        type,
        ...(type === 'agent' ? { agentId: '' } : {}),
        ...(type === 'action' ? { tool: '' } : {}),
        ...(type === 'decision' ? { condition: '' } : {}),
        ...(type === 'input' ? { value: '' } : {}),
        ...(type === 'output' ? { value: '' } : {})
      }
    }

    setNodes((nds) => [...nds, newNode])
    setSelectedNode(newNode)
    setShowPropertiesPanel(true)
    setToolboxOpen(false)
  }

  // Handle node configuration
  const handleNodeConfigChange = (field: string, value: any) => {
    if (selectedNode) {
      const updatedNode: WorkflowNode = {
        ...selectedNode,
        data: {
          ...selectedNode.data,
          [field]: value
        }
      }

      setNodes((nds) => nds.map((node) => (node.id === selectedNode.id ? updatedNode : node)))
      setSelectedNode(updatedNode)
    }
  }

  // Get node configuration component
  const getNodeConfigComponent = () => {
    if (!selectedNode) return null

    switch (selectedNode.type) {
      case 'agent':
        return (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-muted-foreground mb-2">
                Agent
              </label>
              <Select
                value={selectedNode.data.agentId || ''}
                onChange={(e) => handleNodeConfigChange('agentId', e.target.value)}
                className="w-full"
              >
                <option value="">Select an agent...</option>
                {agents.map(agent => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name} ({agent.role})
                  </option>
                ))}
              </Select>
            </div>
            {selectedNode.data.agentId && (
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-2">
                  Agent Tools
                </label>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {mockAgents.find(a => a.id === selectedNode.data.agentId)?.tools.map(tool => (
                    <Badge key={tool} variant="secondary" className="bg-purple-100 text-purple-800">
                      {tool}
                    </Badge>
                  ))}
                </div>
              </div>
            )}
          </div>
        )

      case 'action':
        return (
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-2">
              Tool
            </label>
            <Select
              value={selectedNode.data.tool || ''}
              onChange={(e) => handleNodeConfigChange('tool', e.target.value)}
              className="w-full"
            >
              <option value="">Select a tool...</option>
              {availableTools.map(tool => (
                <option key={tool.name} value={tool.name}>
                  {tool.label}
                </option>
              ))}
            </Select>
          </div>
        )

      case 'decision':
        return (
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-2">
              Condition
            </label>
            <Input
              type="text"
              placeholder="e.g., input.value > 100"
              value={selectedNode.data.condition || ''}
              onChange={(e) => handleNodeConfigChange('condition', e.target.value)}
              className="w-full"
            />
          </div>
        )

      case 'input':
      case 'output':
        return (
          <div>
            <label className="block text-sm font-medium text-muted-foreground mb-2">
              Value/Description
            </label>
            <Input
              type="text"
              placeholder="Enter value or description"
              value={selectedNode.data.value || ''}
              onChange={(e) => handleNodeConfigChange('value', e.target.value)}
              className="w-full"
            />
          </div>
        )

      default:
        return null
    }
  }

  // Node tooltip
  const handleNodeMouseEnter = (nodeId: string) => {
    setTooltippedNode(nodeId)
  }

  const handleNodeMouseLeave = () => {
    setTooltippedNode(null)
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="bg-background/80 backdrop-blur-sm border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <h1 className="text-3xl font-bold text-foreground">Workflow Designer</h1>
            <p className="text-muted-foreground mt-1">
              {workflowId ? 'Edit Workflow' : 'Create New Workflow'}
            </p>
          </div>

          <div className="flex space-x-3">
            <Button
              variant="outline"
              onClick={() => router.back()}
              disabled={loading}
            >
              Cancel
            </Button>
            <Button
              onClick={handleSaveWorkflow}
              disabled={loading}
              loading={loading}
            >
              Save Workflow
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Canvas Area */}
        <div className="flex-1 flex flex-col">
          {/* Toolbar */}
          <div className="bg-background/80 backdrop-blur-sm border-b border-border px-4 py-3">
            <div className="flex items-center space-x-4">
              {/* Toolbox Toggle */}
              <Button
                variant="outline"
                size="sm"
                onClick={() => setToolboxOpen(!toolboxOpen)}
                className="px-3"
              >
                {toolboxOpen ? 'Hide' : 'Show'} Toolbox
              </Button>

              {/* Workflow Actions */}
              <div className="flex space-x-2">
                <Tooltip content="Validate Workflow">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const errors = validateWorkflow()
                      if (errors.length > 0) {
                        alert('Workflow validation errors:\n' + errors.join('\n'))
                      } else {
                        alert('Workflow is valid!')
                      }
                    }}
                  >
                    🔍 Validate
                  </Button>
                </Tooltip>

                <Tooltip content="Run Preview">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRunPreview}
                    disabled={loading}
                  >
                    ▶️ Run Preview
                  </Button>
                </Tooltip>

                <Tooltip content="Zoom In">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => reactFlowInstance.current?.zoomIn()}
                  >
                    +
                  </Button>
                </Tooltip>

                <Tooltip content="Zoom Out">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => reactFlowInstance.current?.zoomOut()}
                  >
                    -
                  </Button>
                </Tooltip>

                <Tooltip content="Fit to View">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => reactFlowInstance.current?.fitView()}
                  >
                    📏
                  </Button>
                </Tooltip>
              </div>

              {/* Node Count */}
              <div className="text-sm text-muted-foreground ml-auto">
                {nodes.length} nodes | {edges.length} edges
              </div>
            </div>
          </div>

          {/* React Flow Canvas */}
          <div className="relative flex-1 bg-surface-2">
            <ReactFlow
              ref={reactFlowInstance}
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              nodeTypes={nodeTypes}
              fitView
              className="flex-1"
              onNodeClick={handleNodeClick}
              onNodeMouseEnter={handleNodeMouseEnter}
              onNodeMouseLeave={handleNodeMouseLeave}
              onPaneClick={() => {
                setSelectedNode(null)
                setShowPropertiesPanel(false)
              }}
              style={{ background: '#f8fafc' }}
            >
              <Controls />
              <MiniMap />
              <Background variant="dots" gap={12} size={1} />
            </ReactFlow>

            {/* Node Tooltip */}
            {tooltippedNode && (
              <div className="absolute bg-black/80 text-white px-3 py-1 rounded-lg text-sm">
                {nodes.find(node => node.id === tooltippedNode)?.data.name || 'Node'}
              </div>
            )}
          </div>
        </div>

        {/* Properties Panel */}
        <div className={`w-80 bg-surface shadow-lg ${showPropertiesPanel ? '' : 'hidden'}`}>
          <div className="h-full flex flex-col">
            <div className="border-b border-border p-4">
              <h2 className="text-lg font-semibold text-foreground">Node Properties</h2>
              {selectedNode && (
                <p className="text-sm text-muted-foreground mt-1">
                  {selectedNode.type.charAt(0).toUpperCase() + selectedNode.type.slice(1)}
                </p>
              )}
            </div>

            <div className="flex-1 overflow-auto p-4 space-y-4">
              {/* Node Name */}
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-2">
                  Node Name
                </label>
                <Input
                  type="text"
                  value={selectedNode?.data.name || ''}
                  onChange={(e) => handleNodeConfigChange('name', e.target.value)}
                  className="w-full"
                />
              </div>

              {/* Node Type */}
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-2">
                  Node Type
                </label>
                <Select
                  value={selectedNode?.type || ''}
                  onChange={(e) => handleNodeTypeChange(e.target.value)}
                  className="w-full"
                  disabled={true}
                >
                  {nodeTypesList.map(type => (
                    <option key={type} value={type}>
                      {type.charAt(0).toUpperCase() + type.slice(1)}
                    </option>
                  ))}
                </Select>
              </div>

              {/* Node Configuration */}
              {getNodeConfigComponent()}

              {/* Position */}
              <div>
                <label className="block text-sm font-medium text-muted-foreground mb-2">
                  Position
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <Input
                    type="number"
                    value={selectedNode?.position.x || 0}
                    onChange={(e) => handleNodeConfigChange('position', { ...selectedNode?.position, x: Number(e.target.value) })}
                    placeholder="X"
                    className="w-full"
                  />
                  <Input
                    type="number"
                    value={selectedNode?.position.y || 0}
                    onChange={(e) => handleNodeConfigChange('position', { ...selectedNode?.position, y: Number(e.target.value) })}
                    placeholder="Y"
                    className="w-full"
                  />
                </div>
              </div>
            </div>

            {/* Actions */}
            <div className="border-t border-border p-4">
              <div className="flex space-x-2">
                <Button
                  variant="outline"
                  onClick={handleDeleteNode}
                  className="flex-1"
                >
                  Delete
                </Button>
                <Button
                  variant="default"
                  onClick={() => setShowPropertiesPanel(false)}
                >
                  Close
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Toolbox */}
      {toolboxOpen && (
        <div className="absolute top-16 left-4 bg-surface shadow-lg rounded-lg p-3">
          <h3 className="text-sm font-medium text-muted-foreground mb-2">Toolbox</h3>
          <div className="grid grid-cols-2 gap-2">
            {nodeTypesList.map((type) => (
              <Button
                key={type}
                variant="outline"
                size="sm"
                onClick={() => handleAddNode(type as any)}
                className="w-full justify-start text-left"
              >
                {type.charAt(0).toUpperCase() + type.slice(1)}
              </Button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// Custom node components
export function AgentNode({ data, selected, onSelect }: { data: NodeData; selected: boolean; onSelect: () => void }) {
  return (
    <div
      className={`flex items-center p-3 rounded-lg ${selected ? 'bg-blue-50 border-2 border-blue-200' : 'bg-surface border border-border'}`}
      onClick={onSelect}
    >
      <div className="w-3 h-3 bg-blue-500 rounded-full mr-3"></div>
      <div>
        <div className="font-medium text-foreground">{data.name}</div>
        <div className="text-sm text-muted-foreground">Agent</div>
      </div>
    </div>
  )
}

export function DecisionNode({ data, selected, onSelect }: { data: NodeData; selected: boolean; onSelect: () => void }) {
  return (
    <div
      className={`flex items-center p-3 rounded-lg bg-gradient-to-r from-yellow-100 to-yellow-50 border-2 border-yellow-200 ${selected ? 'border-2 border-yellow-300' : 'border border-border'}`}
      onClick={onSelect}
    >
      <div className="w-3 h-3 bg-yellow-500 rounded-full mr-3"></div>
      <div>
        <div className="font-medium text-foreground">{data.name}</div>
        <div className="text-sm text-muted-foreground">Decision</div>
      </div>
    </div>
  )
}

export function ActionNode({ data, selected, onSelect }: { data: NodeData; selected: boolean; onSelect: () => void }) {
  return (
    <div
      className={`flex items-center p-3 rounded-lg bg-gradient-to-r from-purple-100 to-purple-50 border-2 border-purple-200 ${selected ? 'border-2 border-purple-300' : 'border border-border'}`}
      onClick={onSelect}
    >
      <div className="w-3 h-3 bg-purple-500 rounded-full mr-3"></div>
      <div>
        <div className="font-medium text-foreground">{data.name}</div>
        <div className="text-sm text-muted-foreground">Action</div>
      </div>
    </div>
  )
}

export function InputNode({ data, selected, onSelect }: { data: NodeData; selected: boolean; onSelect: () => void }) {
  return (
    <div
      className={`flex items-center p-3 rounded-lg bg-gradient-to-r from-green-100 to-green-50 border-2 border-green-200 ${selected ? 'border-2 border-green-300' : 'border border-border'}`}
      onClick={onSelect}
    >
      <div className="w-3 h-3 bg-green-500 rounded-full mr-3"></div>
      <div>
        <div className="font-medium text-foreground">{data.name}</div>
        <div className="text-sm text-muted-foreground">Input</div>
      </div>
    </div>
  )
}

export function OutputNode({ data, selected, onSelect }: { data: NodeData; selected: boolean; onSelect: () => void }) {
  return (
    <div
      className={`flex items-center p-3 rounded-lg bg-gradient-to-r from-red-100 to-red-50 border-2 border-red-200 ${selected ? 'border-2 border-red-300' : 'border border-border'}`}
      onClick={onSelect}
    >
      <div className="w-3 h-3 bg-red-500 rounded-full mr-3"></div>
      <div>
        <div className="font-medium text-foreground">{data.name}</div>
        <div className="text-sm text-muted-foreground">Output</div>
      </div>
    </div>
  )
}
"use client"

import { NodeData, NodeProps } from 'reactflow'

interface AgentNodeData extends NodeData {
  id: string
  name: string
  type: 'agent'
  agentId?: string
  position: { x: number; y: number }
}

export function AgentNode({ data, selected, onSelect }: NodeProps<AgentNodeData>) {
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
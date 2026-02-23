"use client"

import { NodeData, NodeProps } from 'reactflow'

interface ActionNodeData extends NodeData {
  id: string
  name: string
  type: 'action'
  tool?: string
  position: { x: number; y: number }
}

export function ActionNode({ data, selected, onSelect }: NodeProps<ActionNodeData>) {
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
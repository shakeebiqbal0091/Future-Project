"use client"

import { NodeData, NodeProps } from 'reactflow'

interface DecisionNodeData extends NodeData {
  id: string
  name: string
  type: 'decision'
  condition?: string
  position: { x: number; y: number }
}

export function DecisionNode({ data, selected, onSelect }: NodeProps<DecisionNodeData>) {
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
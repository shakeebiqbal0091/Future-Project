"use client"

import { NodeData, NodeProps } from 'reactflow'

interface OutputNodeData extends NodeData {
  id: string
  name: string
  type: 'output'
  value?: string
  position: { x: number; y: number }
}

export function OutputNode({ data, selected, onSelect }: NodeProps<OutputNodeData>) {
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
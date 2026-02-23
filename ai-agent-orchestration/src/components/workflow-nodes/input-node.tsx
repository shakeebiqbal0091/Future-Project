"use client"

import { NodeData, NodeProps } from 'reactflow'

interface InputNodeData extends NodeData {
  id: string
  name: string
  type: 'input'
  value?: string
  position: { x: number; y: number }
}

export function InputNode({ data, selected, onSelect }: NodeProps<InputNodeData>) {
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
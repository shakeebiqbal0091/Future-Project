import React from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Droppable } from 'react-dnd';
import { useToast } from '@/components/ui/toast';

interface NodePaletteProps {
  onNewNode: (nodeType: string, position: { x: number; y: number }) => void;
}

const nodeTypes = [
  {
    id: 'agent',
    label: 'Agent',
    description: 'Execute an AI agent with specific tools and instructions',
    icon: '🤖',
    color: 'bg-blue-500',
  },
  {
    id: 'decision',
    label: 'Decision',
    description: 'Conditional branching based on evaluation criteria',
    icon: '❓',
    color: 'bg-purple-500',
  },
  {
    id: 'action',
    label: 'Action',
    description: 'Perform automated actions like HTTP requests or database operations',
    icon: '⚡',
    color: 'bg-orange-500',
  },
  {
    id: 'human',
    label: 'Human',
    description: 'Pause workflow for human review or input',
    icon: '👤',
    color: 'bg-green-500',
  },
  {
    id: 'branch',
    label: 'Branch',
    description: 'Parallel execution of multiple workflow paths',
    icon: '🌱',
    color: 'bg-pink-500',
  },
  {
    id: 'end',
    label: 'End',
    description: 'Terminate workflow execution',
    icon: '✅',
    color: 'bg-gray-500',
  },
];

const NodePalette: React.FC<NodePaletteProps> = ({ onNewNode }) => {
  const toast = useToast();

  const handleDragStart = (nodeType: string) => {
    toast.info(`Drag ${nodeType} node to canvas`);
  };

  return (
    <div className="space-y-4">
      {nodeTypes.map((node) => (
        <Card key={node.id} className="cursor-move" draggable>
          <CardHeader className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${node.color}`}>
                <span className="text-white font-bold text-sm">{node.icon}</span>
              </div>
              <div>
                <CardTitle className="text-sm font-medium">{node.label}</CardTitle>
                <CardDescription className="text-xs text-gray-500">{node.description}</CardDescription>
              </div>
            </div>
            <Badge variant="outline">{node.id}</Badge>
          </CardHeader>
          <CardContent className="pt-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                const position = { x: 100, y: 100 }; // Default position, will be updated by canvas
                onNewNode(node.id, position);
                toast.success(`${node.label} node added to canvas`);
              }}
            >
              Add to Canvas
            </Button>
          </CardContent>
        </Card>
      ))}
    </div>
  );
};

export default NodePalette;
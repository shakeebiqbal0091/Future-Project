import React, { useState, useCallback } from 'react';
import { Node, Edge, useNodesState, useEdgesState, useSelectedNodesState, useEditorControls, useNodesDraggable, Controls, Background, MiniMap } from 'reactflow';
import { XYPosition, Position, NodeTypes, NodeComponents, NodeData, EdgeData } from 'reactflow/dist/types';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select } from '@/components/ui/select';
import { useToast } from '@/components/ui/toast';

interface WorkflowCanvasProps {
  nodes: Node[];
  edges: Edge[];
  onNodesChange: (nodes: Node[]) => void;
  onNodeSelected: (nodeId: string) => void;
  onNodeUpdated: (updatedNode: Node) => void;
  onNodeDeleted: (nodeId: string) => void;
  onEdgeAdded: (edge: Edge) => void;
  onEdgeRemoved: (edge: Edge) => void;
  selectedNodeId: string | null;
  isValid: boolean;
  loading: boolean;
}

const WorkflowCanvas: React.FC<WorkflowCanvasProps> = ({
  nodes,
  edges,
  onNodesChange,
  onNodeSelected,
  onNodeUpdated,
  onNodeDeleted,
  onEdgeAdded,
  onEdgeRemoved,
  selectedNodeId,
  isValid,
  loading,
}) => {
  const toast = useToast();
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionSource, setConnectionSource] = useState<string | null>(null);

  const handleNodeClick = useCallback((event: React.MouseEvent, node: Node) => {
    onNodeSelected(node.id);
  }, [onNodeSelected]);

  const handleNodeMouseEnter = useCallback((nodeId: string) => {
    setHoveredNode(nodeId);
  }, []);

  const handleNodeMouseLeave = useCallback(() => {
    setHoveredNode(null);
  }, []);

  const handleConnectNodes = useCallback((sourceId: string, targetId: string) => {
    if (sourceId === targetId) {
      toast.error('Cannot connect a node to itself');
      return;
    }

    const existingEdge = edges.find(
      (edge) => edge.source === sourceId && edge.target === targetId
    );
    if (existingEdge) {
      toast.error('Connection already exists');
      return;
    }

    const newEdge: Edge = {
      id: `edge_${sourceId}_${targetId}`,
      source: sourceId,
      target: targetId,
      animated: true,
      type: 'smoothstep',
    };

    onEdgeAdded(newEdge);
    setIsConnecting(false);
    setConnectionSource(null);
  }, [edges, onEdgeAdded, toast]);

  const handleStartConnection = useCallback((sourceId: string) => {
    setIsConnecting(true);
    setConnectionSource(sourceId);
  }, []);

  const handleCancelConnection = useCallback(() => {
    setIsConnecting(false);
    setConnectionSource(null);
  }, []);

  const handleNodePositionChange = useCallback((nodeId: string, position: XYPosition) => {
    const updatedNodes = nodes.map((node) =>
      node.id === nodeId ? { ...node, position } : node
    );
    onNodesChange(updatedNodes);
  }, [nodes, onNodesChange]);

  const handleDeleteNode = useCallback((nodeId: string) => {
    if (window.confirm('Are you sure you want to delete this node?')) {
      onNodeDeleted(nodeId);
    }
  }, [onNodeDeleted]);

  const CustomNode = ({ data, selected, ...props }: any) => {
    const nodeTypes = {
      agent: AgentNode,
      decision: DecisionNode,
      action: ActionNode,
      human: HumanNode,
      branch: BranchNode,
      end: EndNode,
    };

    const NodeType = nodeTypes[data.type] || DefaultNode;

    return <NodeType data={data} selected={selected} {...props} />;
  };

  const AgentNode = ({ data, selected, style, handleSelection }: any) => (
    <div
      className={`p-3 border-2 transition-all ${
        selected
          ? 'border-blue-500 bg-blue-50 shadow-lg'
          : hoveredNode === data.id
          ? 'border-blue-400 bg-blue-50 hover:shadow-md'
          : 'border-gray-200 bg-white hover:shadow-md hover:border-gray-300'
      } ${
        isConnecting && connectionSource === data.id
          ? 'border-blue-500 bg-blue-100'
          : ''
      }`}
      style={style}
      onClick={(e) => handleSelection(e, data.id)}
      onMouseEnter={() => handleNodeMouseEnter(data.id)}
      onMouseLeave={handleNodeMouseLeave}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-blue-600 font-bold">🤖</span>
          <span className="text-sm font-medium">{data.label}</span>
        </div>
        <div className="flex items-center gap-1">
          <Badge variant="outline" className="text-xs">
            {data.config.agent_id || 'No Agent'}
          </Badge>
        </div>
      </div>
      <div className="mt-1 text-xs text-gray-500">
        {data.config.instructions?.substring(0, 50)}...
      </div>
    </div>
  );

  const DecisionNode = ({ data, selected, style, handleSelection }: any) => (
    <div
      className={`p-3 border-2 transition-all ${
        selected
          ? 'border-purple-500 bg-purple-50 shadow-lg'
          : hoveredNode === data.id
          ? 'border-purple-400 bg-purple-50 hover:shadow-md'
          : 'border-gray-200 bg-white hover:shadow-md hover:border-gray-300'
      } ${
        isConnecting && connectionSource === data.id
          ? 'border-purple-500 bg-purple-100'
          : ''
      }`}
      style={style}
      onClick={(e) => handleSelection(e, data.id)}
      onMouseEnter={() => handleNodeMouseEnter(data.id)}
      onMouseLeave={handleNodeMouseLeave}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-purple-600 font-bold">❓</span>
          <span className="text-sm font-medium">{data.label}</span>
        </div>
      </div>
      <div className="mt-1 text-xs text-gray-500">
        {data.config.condition?.substring(0, 50)}...
      </div>
    </div>
  );

  const ActionNode = ({ data, selected, style, handleSelection }: any) => (
    <div
      className={`p-3 border-2 transition-all ${
        selected
          ? 'border-orange-500 bg-orange-50 shadow-lg'
          : hoveredNode === data.id
          ? 'border-orange-400 bg-orange-50 hover:shadow-md'
          : 'border-gray-200 bg-white hover:shadow-md hover:border-gray-300'
      } ${
        isConnecting && connectionSource === data.id
          ? 'border-orange-500 bg-orange-100'
          : ''
      }`}
      style={style}
      onClick={(e) => handleSelection(e, data.id)}
      onMouseEnter={() => handleNodeMouseEnter(data.id)}
      onMouseLeave={handleNodeMouseLeave}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-orange-600 font-bold">⚡</span>
          <span className="text-sm font-medium">{data.label}</span>
        </div>
      </div>
      <div className="mt-1 text-xs text-gray-500">
        {data.config.action_type} - {data.config.url?.substring(0, 50)}...
      </div>
    </div>
  );

  const HumanNode = ({ data, selected, style, handleSelection }: any) => (
    <div
      className={`p-3 border-2 transition-all ${
        selected
          ? 'border-green-500 bg-green-50 shadow-lg'
          : hoveredNode === data.id
          ? 'border-green-400 bg-green-50 hover:shadow-md'
          : 'border-gray-200 bg-white hover:shadow-md hover:border-gray-300'
      } ${
        isConnecting && connectionSource === data.id
          ? 'border-green-500 bg-green-100'
          : ''
      }`}
      style={style}
      onClick={(e) => handleSelection(e, data.id)}
      onMouseEnter={() => handleNodeMouseEnter(data.id)}
      onMouseLeave={handleNodeMouseLeave}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-green-600 font-bold">👤</span>
          <span className="text-sm font-medium">{data.label}</span>
        </div>
      </div>
      <div className="mt-1 text-xs text-gray-500">
        Human review required
      </div>
    </div>
  );

  const BranchNode = ({ data, selected, style, handleSelection }: any) => (
    <div
      className={`p-3 border-2 transition-all ${
        selected
          ? 'border-pink-500 bg-pink-50 shadow-lg'
          : hoveredNode === data.id
          ? 'border-pink-400 bg-pink-50 hover:shadow-md'
          : 'border-gray-200 bg-white hover:shadow-md hover:border-gray-300'
      } ${
        isConnecting && connectionSource === data.id
          ? 'border-pink-500 bg-pink-100'
          : ''
      }`}
      style={style}
      onClick={(e) => handleSelection(e, data.id)}
      onMouseEnter={() => handleNodeMouseEnter(data.id)}
      onMouseLeave={handleNodeMouseLeave}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-pink-600 font-bold">🌱</span>
          <span className="text-sm font-medium">{data.label}</span>
        </div>
      </div>
      <div className="mt-1 text-xs text-gray-500">
        Parallel execution paths
      </div>
    </div>
  );

  const EndNode = ({ data, selected, style, handleSelection }: any) => (
    <div
      className={`p-3 border-2 transition-all ${
        selected
          ? 'border-gray-500 bg-gray-50 shadow-lg'
          : hoveredNode === data.id
          ? 'border-gray-400 bg-gray-50 hover:shadow-md'
          : 'border-gray-200 bg-white hover:shadow-md hover:border-gray-300'
      } ${
        isConnecting && connectionSource === data.id
          ? 'border-gray-500 bg-gray-100'
          : ''
      }`}
      style={style}
      onClick={(e) => handleSelection(e, data.id)}
      onMouseEnter={() => handleNodeMouseEnter(data.id)}
      onMouseLeave={handleNodeMouseLeave}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-gray-600 font-bold">✅</span>
          <span className="text-sm font-medium">{data.label}</span>
        </div>
      </div>
      <div className="mt-1 text-xs text-gray-500">
        Workflow completion
      </div>
    </div>
  );

  const DefaultNode = ({ data, selected, style, handleSelection }: any) => (
    <div
      className={`p-3 border-2 transition-all ${
        selected
          ? 'border-gray-500 bg-gray-50 shadow-lg'
          : hoveredNode === data.id
          ? 'border-gray-400 bg-gray-50 hover:shadow-md'
          : 'border-gray-200 bg-white hover:shadow-md hover:border-gray-300'
      } ${
        isConnecting && connectionSource === data.id
          ? 'border-gray-500 bg-gray-100'
          : ''
      }`}
      style={style}
      onClick={(e) => handleSelection(e, data.id)}
      onMouseEnter={() => handleNodeMouseEnter(data.id)}
      onMouseLeave={handleNodeMouseLeave}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-gray-600 font-bold">🔌</span>
          <span className="text-sm font-medium">{data.label}</span>
        </div>
      </div>
      <div className="mt-1 text-xs text-gray-500">
        Unknown node type
      </div>
    </div>
  );

  return (
    <div className="relative">
      <div className="flex items-center justify-between mb-4">
        <Button
          variant="outline"
          size="sm"
          onClick={handleCancelConnection}
          disabled={!isConnecting}
          className="mr-2"
        >
          Cancel Connection
        </Button>
        <div className="flex items-center gap-2">
          <Badge variant="secondary">
            {nodes.length} nodes
          </Badge>
          <Badge variant="secondary">
            {edges.length} connections
          </Badge>
        </div>
      </div>

      <div className="flex-1 bg-gray-100 rounded-lg border border-gray-200 overflow-hidden h-96">
        <div className="h-full">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgeAdded}
            onConnect={(params) => handleConnectNodes(params.source, params.target)}
            onNodeClick={handleNodeClick}
            onNodeDragStop={(event, node) => handleNodePositionChange(node.id, node.position)}
            nodeTypes={{ default: CustomNode }}
            fitView
            className="bg-white"
            style={{ height: '100%' }}
            onLoad={(reactFlowInstance) => reactFlowInstance.fitView()}
            connectionLineComponent={(props) => (
              <div
                style={{
                  ...props.style,
                  backgroundColor: isValid ? '#8b5cf6' : '#ef4444',
                  pointerEvents: 'none',
                }}
              />
            )}
            connectionLineStyle={{
              strokeWidth: 2,
              stroke: isValid ? '#8b5cf6' : '#ef4444',
            }}
            connectionLineType="smoothstep"
            minZoom={0.5}
            maxZoom={2}
          >
            <Controls />
            <Background variant="dots" gap={12} size={1} />
            <MiniMap
              style={{ background: '#f8f9fa' }}
              nodeColor={(node) => {
                if (node.selected) return '#8b5cf6';
                if (node.type === 'agent') return '#3b82f6';
                if (node.type === 'decision') return '#a855f7';
                if (node.type === 'action') return '#f97316';
                if (node.type === 'human') return '#10b981';
                if (node.type === 'branch') return '#ec4899';
                if (node.type === 'end') return '#6b7280';
                return '#9ca3af';
              }}
            />
          </ReactFlow>
        </div>
      </div>
    </div>
  );
};

export default WorkflowCanvas;
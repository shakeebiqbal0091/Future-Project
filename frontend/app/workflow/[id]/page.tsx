'use client'

import { useState, useEffect, useCallback } from 'react';
import { useParams, useRouter } from 'next/router';
import { Node, Edge, useNodesState, useEdgesState, useSelectedNodesState, useEditorControls, useNodesDraggable, Controls, Background, MiniMap } from 'reactflow';
import { XYPosition, Position, NodeTypes, NodeComponents, NodeData, EdgeData } from 'reactflow/dist/types';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ButtonGroup } from '@/components/ui/button-group';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Spinner } from '@/components/ui/spinner';
import { useToast } from '@/components/ui/toast';
import { useApi } from '@/hooks/use-api';
import NodePalette from '@/components/workflow/NodePalette';
import WorkflowCanvas from '@/components/workflow/WorkflowCanvas';
import WorkflowInspector from '@/components/workflow/WorkflowInspector';
import WorkflowValidation from '@/components/workflow/WorkflowValidation';

interface WorkflowParams {
  id?: string;
}

interface Workflow {
  id: string;
  name: string;
  description: string;
  definition: any;
  status: 'draft' | 'active' | 'archived';
  created_at: string;
  updated_at: string;
}

const WorkflowBuilderPage: React.FC = () => {
  const { id } = useParams<WorkflowParams>();
  const router = useRouter();
  const toast = useToast();
  const { user } = useAuth();

  // API hooks
  const { data: workflowData, isLoading: loadingWorkflow, mutate } = useApi<Workflow>(
    id && id !== 'new' ? `/api/v1/workflows/${id}` : null
  );

  const { mutate: saveWorkflow } = useApi(
    id && id !== 'new' ? `/api/v1/workflows/${id}` : '/api/v1/workflows',
    {
      method: id && id !== 'new' ? 'PUT' : 'POST',
      onSuccess: () => {
        toast.success(`Workflow ${id && id !== 'new' ? 'updated' : 'created'} successfully!`);
        if (id && id !== 'new') {
          mutate();
        } else {
          router.push(`/workflow/${response?.id || '1'}`);
        }
      },
      onError: (error) => {
        toast.error(`Failed to save workflow: ${error.message}`);
      },
    }
  );

  // State
  const [workflow, setWorkflow] = useState<Workflow>({
    id: id || '',
    name: workflowData?.name || 'Untitled Workflow',
    description: workflowData?.description || '',
    definition: workflowData?.definition || { nodes: [], edges: [] },
    status: workflowData?.status || 'draft',
    created_at: workflowData?.created_at || new Date().toISOString(),
    updated_at: workflowData?.updated_at || new Date().toISOString(),
  });

  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [isWorkflowValid, setIsWorkflowValid] = useState(true);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [isSaving, setIsSaving] = useState(false);

  // Initialize workflow
  useEffect(() => {
    if (workflowData) {
      setWorkflow(workflowData);
    }
  }, [workflowData]);

  // Handle workflow changes
  const handleWorkflowChange = useCallback((definition: any) => {
    setWorkflow((prev) => ({
      ...prev,
      definition,
      updated_at: new Date().toISOString(),
    }));
    validateWorkflow(definition);
  }, []);

  // Workflow validation
  const validateWorkflow = useCallback((definition: any) => {
    const errors = [];

    // Check for cycles
    const hasCycle = detectCycle(definition.nodes, definition.edges);
    if (hasCycle) {
      errors.push('Workflow contains a cycle - this will cause infinite loops!');
    }

    // Check for disconnected nodes
    const connectedNodes = new Set();
    definition.edges.forEach((edge: any) => {
      connectedNodes.add(edge.source);
      connectedNodes.add(edge.target);
    });
    const disconnectedNodes = definition.nodes.filter(
      (node: any) => !connectedNodes.has(node.id)
    );
    if (disconnectedNodes.length > 0) {
      errors.push(`Found ${disconnectedNodes.length} disconnected node(s): ${disconnectedNodes.map((n: any) => n.data.label).join(', ')}`);
    }

    // Check for multiple start nodes
    const startNodes = definition.nodes.filter((node: any) => {
      return !definition.edges.find((edge: any) => edge.target === node.id);
    });
    if (startNodes.length > 1) {
      errors.push(`Found ${startNodes.length} start nodes. Workflows should have exactly one entry point.`);
    }

    // Check for multiple end nodes
    const endNodes = definition.nodes.filter((node: any) => {
      return !definition.edges.find((edge: any) => edge.source === node.id);
    });
    if (endNodes.length > 1) {
      errors.push(`Found ${endNodes.length} end nodes. Consider using a single end node for clarity.`);
    }

    setIsWorkflowValid(errors.length === 0);
    setValidationErrors(errors);
  }, []);

  // Cycle detection algorithm
  const detectCycle = useCallback((nodes: any[], edges: any[]) => {
    const graph: { [key: string]: string[] } = {};

    edges.forEach((edge: any) => {
      if (!graph[edge.source]) graph[edge.source] = [];
      graph[edge.source].push(edge.target);
    });

    const visited = new Set();
    const recStack = new Set();

    function hasCycle(node: string): boolean {
      if (!visited.has(node)) {
        visited.add(node);
        recStack.add(node);

        const neighbors = graph[node] || [];
        for (const neighbor of neighbors) {
          if (!visited.has(neighbor) && hasCycle(neighbor)) {
            return true;
          } else if (recStack.has(neighbor)) {
            return true;
          }
        }
      }
      recStack.delete(node);
      return false;
    }

    for (const node of nodes) {
      if (hasCycle(node.id)) {
        return true;
      }
    }

    return false;
  }, []);

  // Save workflow
  const handleSave = useCallback(async () => {
    if (!isWorkflowValid) {
      toast.error('Cannot save workflow - validation errors found!');
      return;
    }

    setIsSaving(true);
    try {
      await saveWorkflow({
        name: workflow.name,
        description: workflow.description,
        definition: workflow.definition,
        status: workflow.status,
      });
    } finally {
      setIsSaving(false);
    }
  }, [workflow, isWorkflowValid, saveWorkflow, toast]);

  // Test workflow
  const handleTest = useCallback(async () => {
    if (!isWorkflowValid) {
      toast.error('Cannot test workflow - validation errors found!');
      return;
    }

    try {
      const response = await fetch(`/api/v1/workflows/${workflow.id}/test`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          input: {}, // Test with empty input
        }),
      });

      if (response.ok) {
        const result = await response.json();
        toast.success(`Workflow test completed successfully! Results: ${result.status}`);
      } else {
        const error = await response.json();
        toast.error(`Workflow test failed: ${error.message}`);
      }
    } catch (error) {
      toast.error(`Failed to test workflow: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }, [workflow.id, toast]);

  // Run workflow
  const handleRun = useCallback(async () => {
    if (!isWorkflowValid) {
      toast.error('Cannot run workflow - validation errors found!');
      return;
    }

    try {
      const response = await fetch(`/api/v1/workflows/${workflow.id}/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          input: {}, // Run with empty input
        }),
      });

      if (response.ok) {
        const result = await response.json();
        toast.success(`Workflow started successfully! Run ID: ${result.run_id}`);
        router.push(`/workflow-runs/${result.run_id}`);
      } else {
        const error = await response.json();
        toast.error(`Failed to run workflow: ${error.message}`);
      }
    } catch (error) {
      toast.error(`Failed to run workflow: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  }, [workflow.id, toast, router]);

  // Handle node selection
  const handleNodeSelected = useCallback((nodeId: string) => {
    setSelectedNode(nodeId);
  }, []);

  // Handle node updates
  const handleNodeUpdated = useCallback((updatedNode: any) => {
    const updatedDefinition = {
      ...workflow.definition,
      nodes: workflow.definition.nodes.map((node: any) =>
        node.id === updatedNode.id ? updatedNode : node
      ),
    };
    handleWorkflowChange(updatedDefinition);
  }, [workflow.definition, handleWorkflowChange]);

  // Handle node deletion
  const handleNodeDeleted = useCallback((nodeId: string) => {
    const updatedDefinition = {
      ...workflow.definition,
      nodes: workflow.definition.nodes.filter((node: any) => node.id !== nodeId),
      edges: workflow.definition.edges.filter(
        (edge: any) => edge.source !== nodeId && edge.target !== nodeId
      ),
    };
    handleWorkflowChange(updatedDefinition);
    setSelectedNode(null);
  }, [workflow.definition, handleWorkflowChange]);

  // Handle edge addition
  const handleEdgeAdded = useCallback((edge: any) => {
    const updatedDefinition = {
      ...workflow.definition,
      edges: [...workflow.definition.edges, edge],
    };
    handleWorkflowChange(updatedDefinition);
  }, [workflow.definition, handleWorkflowChange]);

  // Handle edge removal
  const handleEdgeRemoved = useCallback((edge: any) => {
    const updatedDefinition = {
      ...workflow.definition,
      edges: workflow.definition.edges.filter((e: any) => e.id !== edge.id),
    };
    handleWorkflowChange(updatedDefinition);
  }, [workflow.definition, handleWorkflowChange]);

  // Handle new node creation
  const handleNewNode = useCallback((nodeType: string, position: any) => {
    const newNode = {
      id: `node_${Date.now()}`,
      position,
      type: nodeType,
      data: {
        label: `${nodeType.charAt(0).toUpperCase()}${nodeType.slice(1)} ${Date.now()}`,
        type: nodeType,
        config: getDefaultConfig(nodeType),
      },
    };

    const updatedDefinition = {
      ...workflow.definition,
      nodes: [...workflow.definition.nodes, newNode],
    };
    handleWorkflowChange(updatedDefinition);
    setSelectedNode(newNode.id);
  }, [workflow.definition, handleWorkflowChange]);

  // Get default config for node types
  const getDefaultConfig = useCallback((nodeType: string) => {
    const defaults = {
      agent: {
        agent_id: '',
        instructions: '',
        tools: [],
        timeout: 30,
      },
      decision: {
        condition: '',
        true_branch: '',
        false_branch: '',
      },
      action: {
        action_type: 'http_request',
        url: '',
        method: 'GET',
        headers: {},
        body: '',
      },
      human: {
        assignee: '',
        instructions: '',
      },
      branch: {
        branch_type: 'parallel',
        branches: [],
      },
      end: {
        completion_type: 'success',
        message: '',
      },
    };

    return defaults[nodeType as keyof typeof defaults] || {};
  }, []);

  // Handle workflow name change
  const handleWorkflowNameChange = useCallback((name: string) => {
    setWorkflow((prev) => ({ ...prev, name }));
  }, []);

  // Handle workflow description change
  const handleWorkflowDescriptionChange = useCallback((description: string) => {
    setWorkflow((prev) => ({ ...prev, description }));
  }, []);

  // Handle workflow status change
  const handleWorkflowStatusChange = useCallback((status: 'draft' | 'active' | 'archived') => {
    setWorkflow((prev) => ({ ...prev, status }));
  }, []);

  // Handle preview
  const handlePreview = useCallback(() => {
    setIsDialogOpen(true);
  }, []);

  // Handle dialog close
  const handleDialogClose = useCallback(() => {
    setIsDialogOpen(false);
  }, []);

  if (!isAuthenticated) {
    return null; // Handled by parent
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {id && id !== 'new' ? 'Edit Workflow' : 'Create New Workflow'}
            </h1>
            <p className="text-gray-600 mt-1">
              {id && id !== 'new'
                ? `Workflow ID: ${id}`
                : 'Create and design your AI agent workflows'}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => router.push('/workflows')}
              className="px-4 py-2 border border-gray-300 bg-white text-gray-700 rounded-md hover:bg-gray-50 transition-colors"
            >
              Back to Workflows
            </button>
            <span className="text-sm text-gray-500">
              {user?.email}
            </span>
          </div>
        </div>

        {/* Workflow Properties */}
        <div className="mb-6">
          <Card>
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <Input
                    placeholder="Workflow Name"
                    value={workflow.name}
                    onChange={(e) => handleWorkflowNameChange(e.target.value)}
                    className="text-lg font-semibold"
                    disabled={loadingWorkflow}
                  />
                </div>
                <div className="ml-4">
                  <Select
                    value={workflow.status}
                    onChange={(e) => handleWorkflowStatusChange(e.target.value as any)}
                    disabled={loadingWorkflow}
                    className="text-sm"
                  >
                    <Select.Option value="draft">Draft</Select.Option>
                    <Select.Option value="active">Active</Select.Option>
                    <Select.Option value="archived">Archived</Select.Option>
                  </Select>
                </div>
              </div>
              <Textarea
                placeholder="Workflow description..."
                value={workflow.description}
                onChange={(e) => handleWorkflowDescriptionChange(e.target.value)}
                className="mt-2"
                disabled={loadingWorkflow}
                rows={2}
              />
            </CardContent>
          </Card>
        </div>

        {/* Main Content - Builder Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-6 gap-6">
          {/* Left Sidebar - Node Palette */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle>Node Palette</CardTitle>
                <CardDescription>Drag and drop nodes to build your workflow</CardDescription>
              </CardHeader>
              <CardContent>
                <NodePalette onNewNode={handleNewNode} />
              </CardContent>
            </Card>
          </div>

          {/* Center - Canvas */}
          <div className="lg:col-span-4">
            <Card>
              <CardHeader>
                <CardTitle>Workflow Canvas</CardTitle>
                <CardDescription className="flex items-center gap-2">
                  <Badge variant="secondary">{workflow.definition.nodes.length} nodes</Badge>
                  <Badge variant="secondary">{workflow.definition.edges.length} connections</Badge>
                  <Badge
                    variant={isWorkflowValid ? 'success' : 'destructive'}
                    className={`ml-auto ${!isWorkflowValid ? 'animate-pulse' : ''}`}
                  >
                    {isWorkflowValid ? 'Valid' : 'Invalid'}
                  </Badge>
                </CardDescription>
              </CardHeader>
              <CardContent className="h-96">
                <WorkflowCanvas
                  nodes={workflow.definition.nodes}
                  edges={workflow.definition.edges}
                  onNodesChange={handleWorkflowChange}
                  onNodeSelected={handleNodeSelected}
                  onNodeUpdated={handleNodeUpdated}
                  onNodeDeleted={handleNodeDeleted}
                  onEdgeAdded={handleEdgeAdded}
                  onEdgeRemoved={handleEdgeRemoved}
                  selectedNodeId={selectedNode}
                  isValid={isWorkflowValid}
                  loading={loadingWorkflow}
                />
              </CardContent>
            </Card>
          </div>

          {/* Right Sidebar - Inspector */}
          <div className="lg:col-span-1">
            <Card>
              <CardHeader>
                <CardTitle>Inspector</CardTitle>
                <CardDescription>View and edit node properties</CardDescription>
              </CardHeader>
              <CardContent className="h-96 overflow-y-auto">
                {selectedNode ? (
                  <WorkflowInspector
                    node={workflow.definition.nodes.find((n: any) => n.id === selectedNode)}
                    onNodeUpdated={handleNodeUpdated}
                  />
                ) : (
                  <div className="text-center text-gray-500 py-8">
                    <p>Select a node to view its properties</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Bottom Panel - Validation & Actions */}
        <Card className="mt-6">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <WorkflowValidation
                isValid={isWorkflowValid}
                errors={validationErrors}
                className="flex-1 mr-4"
              />
              <ButtonGroup>
                <Button
                  variant="outline"
                  onClick={handlePreview}
                  disabled={loadingWorkflow}
                >
                  Preview
                </Button>
                <Button
                  onClick={handleTest}
                  disabled={loadingWorkflow || !isWorkflowValid}
                >
                  Test
                </Button>
                <Button
                  onClick={handleRun}
                  disabled={loadingWorkflow || !isWorkflowValid}
                >
                  Run
                </Button>
                <Button
                  onClick={handleSave}
                  disabled={loadingWorkflow || !isWorkflowValid || isSaving}
                  className="bg-blue-600 hover:bg-blue-700"
                >
                  {isSaving ? <Spinner className="mr-2" /> : null}
                  Save
                </Button>
              </ButtonGroup>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Preview Dialog */}
      <Dialog open={isDialogOpen} onOpenChange={handleDialogClose}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>Workflow Preview</DialogTitle>
            <DialogDescription>View your workflow as a flowchart</DialogDescription>
          </DialogHeader>
          <div className="h-96 bg-gray-100 rounded-md p-4">
            <div className="text-center text-gray-500">
              <p>Preview not yet implemented</p>
              <p className="mt-2 text-sm">Real-time workflow visualization coming soon!</p>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

// Mock useAuth hook for this component
const useAuth = () => ({
  user: { email: 'user@example.com' },
  isAuthenticated: true,
});

export default WorkflowBuilderPage;
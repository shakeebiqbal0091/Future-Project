import React, { useState, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Select } from '@/components/ui/select';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useToast } from '@/components/ui/toast';
import { useApi } from '@/hooks/use-api';

interface WorkflowInspectorProps {
  node: any;
  onNodeUpdated: (updatedNode: any) => void;
}

const WorkflowInspector: React.FC<WorkflowInspectorProps> = ({ node, onNodeUpdated }) => {
  const toast = useToast();
  const { data: agents, isLoading: loadingAgents } = useApi(
    '/api/v1/agents',
    { staleTime: 60000 }
  );

  const [localNode, setLocalNode] = useState(node);
  const [isSaving, setIsSaving] = useState(false);

  const handleNodeChange = useCallback((updatedNode: any) => {
    setLocalNode(updatedNode);
    onNodeUpdated(updatedNode);
  }, [onNodeUpdated]);

  const handleSaveNode = useCallback(async () => {
    setIsSaving(true);
    try {
      // Here you would typically save to API, but for now we just update local state
      onNodeUpdated(localNode);
      toast.success('Node configuration saved');
    } catch (error) {
      toast.error('Failed to save node configuration');
    } finally {
      setIsSaving(false);
    }
  }, [localNode, onNodeUpdated, toast]);

  const renderAgentConfig = useCallback(() => {
    if (!localNode) return null;

    return (
      <div className="space-y-4">
        <Input
          label="Node Name"
          value={localNode.data.label}
          onChange={(e) => {
            const updatedNode = { ...localNode, data: { ...localNode.data, label: e.target.value } };
            handleNodeChange(updatedNode);
          }}
          disabled={isSaving}
        />

        <Select
          label="Agent"
          value={localNode.data.config.agent_id}
          onChange={(e) => {
            const updatedNode = {
              ...localNode,
              data: {
                ...localNode.data,
                config: { ...localNode.data.config, agent_id: e.target.value },
              },
            };
            handleNodeChange(updatedNode);
          }}
          disabled={isSaving}
        >
          <Select.Option value="">Select Agent...</Select.Option>
          {agents?.map((agent: any) => (
            <Select.Option key={agent.id} value={agent.id}>
              {agent.name} ({agent.role})
            </Select.Option>
          ))}
        </Select>

        <Textarea
          label="Instructions"
          value={localNode.data.config.instructions || ''}
          onChange={(e) => {
            const updatedNode = {
              ...localNode,
              data: {
                ...localNode.data,
                config: { ...localNode.data.config, instructions: e.target.value },
              },
            };
            handleNodeChange(updatedNode);
          }}
          disabled={isSaving}
          rows={4}
        />

        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => handleNodeChange(localNode)} // Reset to saved state
            disabled={isSaving}
          >
            Reset
          </Button>
          <Button
            onClick={handleSaveNode}
            disabled={isSaving}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {isSaving ? <span>Saving...</span> : <span>Save</span>}
          </Button>
        </div>
      </div>
    );
  }, [localNode, agents, isSaving, handleNodeChange, onNodeUpdated, handleSaveNode]);

  const renderDecisionConfig = useCallback(() => {
    if (!localNode) return null;

    return (
      <div className="space-y-4">
        <Input
          label="Node Name"
          value={localNode.data.label}
          onChange={(e) => {
            const updatedNode = { ...localNode, data: { ...localNode.data, label: e.target.value } };
            handleNodeChange(updatedNode);
          }}
          disabled={isSaving}
        />

        <Textarea
          label="Condition"
          value={localNode.data.config.condition || ''}
          onChange={(e) => {
            const updatedNode = {
              ...localNode,
              data: {
                ...localNode.data,
                config: { ...localNode.data.config, condition: e.target.value },
              },
            };
            handleNodeChange(updatedNode);
          }}
          disabled={isSaving}
          rows={3}
          placeholder="e.g., task.output.status === 'approved'"
        />

        <Input
          label="True Branch"
          value={localNode.data.config.true_branch || ''}
          onChange={(e) => {
            const updatedNode = {
              ...localNode,
              data: {
                ...localNode.data,
                config: { ...localNode.data.config, true_branch: e.target.value },
              },
            };
            handleNodeChange(updatedNode);
          }}
          disabled={isSaving}
          placeholder="Label of node to execute if condition is true"
        />

        <Input
          label="False Branch"
          value={localNode.data.config.false_branch || ''}
          onChange={(e) => {
            const updatedNode = {
              ...localNode,
              data: {
                ...localNode.data,
                config: { ...localNode.data.config, false_branch: e.target.value },
              },
            };
            handleNodeChange(updatedNode);
          }}
          disabled={isSaving}
          placeholder="Label of node to execute if condition is false"
        />

        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => handleNodeChange(localNode)} // Reset to saved state
            disabled={isSaving}
          >
            Reset
          </Button>
          <Button
            onClick={handleSaveNode}
            disabled={isSaving}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {isSaving ? <span>Saving...</span> : <span>Save</span>}
          </Button>
        </div>
      </div>
    );
  }, [localNode, isSaving, handleNodeChange, onNodeUpdated, handleSaveNode]);

  const renderActionConfig = useCallback(() => {
    if (!localNode) return null;

    return (
      <div className="space-y-4">
        <Input
          label="Node Name"
          value={localNode.data.label}
          onChange={(e) => {
            const updatedNode = { ...localNode, data: { ...localNode.data, label: e.target.value } };
            handleNodeChange(updatedNode);
          }}
          disabled={isSaving}
        />

        <Select
          label="Action Type"
          value={localNode.data.config.action_type || 'http_request'}
          onChange={(e) => {
            const updatedNode = {
              ...localNode,
              data: {
                ...localNode.data,
                config: { ...localNode.data.config, action_type: e.target.value },
              },
            };
            handleNodeChange(updatedNode);
          }}
          disabled={isSaving}
        >
          <Select.Option value="http_request">HTTP Request</Select.Option>
          <Select.Option value="database_query">Database Query</Select.Option>
          <Select.Option value="email_send">Send Email</Select.Option>
          <Select.Option value="slack_post">Post to Slack</Select.Option>
        </Select>

        <Input
          label="URL/Endpoint"
          value={localNode.data.config.url || ''}
          onChange={(e) => {
            const updatedNode = {
              ...localNode,
              data: {
                ...localNode.data,
                config: { ...localNode.data.config, url: e.target.value },
              },
            };
            handleNodeChange(updatedNode);
          }}
          disabled={isSaving}
          placeholder="https://api.example.com/endpoint"
        />

        <Select
          label="Method"
          value={localNode.data.config.method || 'GET'}
          onChange={(e) => {
            const updatedNode = {
              ...localNode,
              data: {
                ...localNode.data,
                config: { ...localNode.data.config, method: e.target.value },
              },
            };
            handleNodeChange(updatedNode);
          }}
          disabled={isSaving}
        >
          <Select.Option value="GET">GET</Select.Option>
          <Select.Option value="POST">POST</Select.Option>
          <Select.Option value="PUT">PUT</Select.Option>
          <Select.Option value="DELETE">DELETE</Select.Option>
        </Select>

        <Textarea
          label="Headers (JSON)"
          value={JSON.stringify(localNode.data.config.headers || {}, null, 2)}
          onChange={(e) => {
            try {
              const headers = JSON.parse(e.target.value);
              const updatedNode = {
                ...localNode,
                data: {
                  ...localNode.data,
                  config: { ...localNode.data.config, headers },
                },
              };
              handleNodeChange(updatedNode);
            } catch (error) {
              toast.error('Invalid JSON format');
            }
          }}
          disabled={isSaving}
          rows={4}
          placeholder='{"Content-Type": "application/json"}'
        />

        <Textarea
          label="Body (JSON)"
          value={JSON.stringify(localNode.data.config.body || '', null, 2)}
          onChange={(e) => {
            try {
              const body = JSON.parse(e.target.value);
              const updatedNode = {
                ...localNode,
                data: {
                  ...localNode.data,
                  config: { ...localNode.data.config, body },
                },
              };
              handleNodeChange(updatedNode);
            } catch (error) {
              toast.error('Invalid JSON format');
            }
          }}
          disabled={isSaving}
          rows={4}
          placeholder='{"key": "value"}'
        />

        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => handleNodeChange(localNode)} // Reset to saved state
            disabled={isSaving}
          >
            Reset
          </Button>
          <Button
            onClick={handleSaveNode}
            disabled={isSaving}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {isSaving ? <span>Saving...</span> : <span>Save</span>}
          </Button>
        </div>
      </div>
    );
  }, [localNode, isSaving, handleNodeChange, onNodeUpdated, handleSaveNode, toast]);

  const renderHumanConfig = useCallback(() => {
    if (!localNode) return null;

    return (
      <div className="space-y-4">
        <Input
          label="Node Name"
          value={localNode.data.label}
          onChange={(e) => {
            const updatedNode = { ...localNode, data: { ...localNode.data, label: e.target.value } };
            handleNodeChange(updatedNode);
          }}
          disabled={isSaving}
        />

        <Select
          label="Assignee"
          value={localNode.data.config.assignee || ''}
          onChange={(e) => {
            const updatedNode = {
              ...localNode,
              data: {
                ...localNode.data,
                config: { ...localNode.data.config, assignee: e.target.value },
              },
            };
            handleNodeChange(updatedNode);
          }}
          disabled={isSaving}
        >
          <Select.Option value="">Select Assignee...</Select.Option>
          <Select.Option value="team_lead">Team Lead</Select.Option>
          <Select.Option value="manager">Manager</Select.Option>
          <Select.Option value="admin">Admin</Select.Option>
          <Select.Option value="any">Any Team Member</Select.Option>
        </Select>

        <Textarea
          label="Instructions"
          value={localNode.data.config.instructions || ''}
          onChange={(e) => {
            const updatedNode = {
              ...localNode,
              data: {
                ...localNode.data,
                config: { ...localNode.data.config, instructions: e.target.value },
              },
            };
            handleNodeChange(updatedNode);
          }}
          disabled={isSaving}
          rows={4}
        />

        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => handleNodeChange(localNode)} // Reset to saved state
            disabled={isSaving}
          >
            Reset
          </Button>
          <Button
            onClick={handleSaveNode}
            disabled={isSaving}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {isSaving ? <span>Saving...</span> : <span>Save</span>}
          </Button>
        </div>
      </div>
    );
  }, [localNode, isSaving, handleNodeChange, onNodeUpdated, handleSaveNode]);

  const renderBranchConfig = useCallback(() => {
    if (!localNode) return null;

    return (
      <div className="space-y-4">
        <Input
          label="Node Name"
          value={localNode.data.label}
          onChange={(e) => {
            const updatedNode = { ...localNode, data: { ...localNode.data, label: e.target.value } };
            handleNodeChange(updatedNode);
          }}
          disabled={isSaving}
        />

        <Select
          label="Branch Type"
          value={localNode.data.config.branch_type || 'parallel'}
          onChange={(e) => {
            const updatedNode = {
              ...localNode,
              data: {
                ...localNode.data,
                config: { ...localNode.data.config, branch_type: e.target.value },
              },
            };
            handleNodeChange(updatedNode);
          }}
          disabled={isSaving}
        >
          <Select.Option value="parallel">Parallel Execution</Select.Option>
          <Select.Option value="conditional">Conditional Execution</Select.Option>
        </Select>

        <div className="space-y-2">
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Branch Labels (comma-separated)
          </label>
          <Input
            value={localNode.data.config.branches?.join(', ') || ''}
            onChange={(e) => {
              const branches = e.target.value.split(',').map((b: string) => b.trim()).filter(Boolean);
              const updatedNode = {
                ...localNode,
                data: {
                  ...localNode.data,
                  config: { ...localNode.data.config, branches },
                },
              };
              handleNodeChange(updatedNode);
            }}
            disabled={isSaving}
            placeholder="Branch 1, Branch 2, Branch 3"
          />
        </div>

        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => handleNodeChange(localNode)} // Reset to saved state
            disabled={isSaving}
          >
            Reset
          </Button>
          <Button
            onClick={handleSaveNode}
            disabled={isSaving}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {isSaving ? <span>Saving...</span> : <span>Save</span>}
          </Button>
        </div>
      </div>
    );
  }, [localNode, isSaving, handleNodeChange, onNodeUpdated, handleSaveNode]);

  const renderEndConfig = useCallback(() => {
    if (!localNode) return null;

    return (
      <div className="space-y-4">
        <Input
          label="Node Name"
          value={localNode.data.label}
          onChange={(e) => {
            const updatedNode = { ...localNode, data: { ...localNode.data, label: e.target.value } };
            handleNodeChange(updatedNode);
          }}
          disabled={isSaving}
        />

        <Select
          label="Completion Type"
          value={localNode.data.config.completion_type || 'success'}
          onChange={(e) => {
            const updatedNode = {
              ...localNode,
              data: {
                ...localNode.data,
                config: { ...localNode.data.config, completion_type: e.target.value },
              },
            };
            handleNodeChange(updatedNode);
          }}
          disabled={isSaving}
        >
          <Select.Option value="success">Success</Select.Option>
          <Select.Option value="failure">Failure</Select.Option>
          <Select.Option value="timeout">Timeout</Select.Option>
          <Select.Option value="cancelled">Cancelled</Select.Option>
        </Select>

        <Textarea
          label="Completion Message"
          value={localNode.data.config.message || ''}
          onChange={(e) => {
            const updatedNode = {
              ...localNode,
              data: {
                ...localNode.data,
                config: { ...localNode.data.config, message: e.target.value },
              },
            };
            handleNodeChange(updatedNode);
          }}
          disabled={isSaving}
          rows={3}
          placeholder="Final message to display upon workflow completion"
        />

        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => handleNodeChange(localNode)} // Reset to saved state
            disabled={isSaving}
          >
            Reset
          </Button>
          <Button
            onClick={handleSaveNode}
            disabled={isSaving}
            className="bg-blue-600 hover:bg-blue-700"
          >
            {isSaving ? <span>Saving...</span> : <span>Save</span>}
          </Button>
        </div>
      </div>
    );
  }, [localNode, isSaving, handleNodeChange, onNodeUpdated, handleSaveNode]);

  if (!node) {
    return (
      <div className="text-center text-gray-500 py-8">
        <p>Select a node to view its properties</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>Node Configuration</CardTitle>
          <CardDescription>View and edit {node.data.label} properties</CardDescription>
        </CardHeader>
        <CardContent>
          {node.data.type === 'agent' && renderAgentConfig()}
          {node.data.type === 'decision' && renderDecisionConfig()}
          {node.data.type === 'action' && renderActionConfig()}
          {node.data.type === 'human' && renderHumanConfig()}
          {node.data.type === 'branch' && renderBranchConfig()}
          {node.data.type === 'end' && renderEndConfig()}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Node Information</CardTitle>
          <CardDescription>Basic node details</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-600">Node Type:</span>
              <Badge variant="secondary">{node.data.type}</Badge>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-600">Node ID:</span>
              <span className="text-sm text-gray-500 font-mono">{node.id}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-gray-600">Position:</span>
              <span className="text-sm text-gray-500">
                ({Math.round(node.position.x)}, {Math.round(node.position.y)})
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Node Actions</CardTitle>
          <CardDescription>Manage this node</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            <Button
              onClick={() => handleNodeChange(node)} // Reset to saved state
              className="w-full"
              disabled={isSaving}
            >
              Reset to Saved
            </Button>
            <Button
              variant="destructive"
              onClick={() => {
                if (window.confirm('Are you sure you want to delete this node?')) {
                  onNodeUpdated(node); // This will trigger deletion
                }
              }}
              className="w-full"
              disabled={isSaving}
            >
              Delete Node
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default WorkflowInspector;
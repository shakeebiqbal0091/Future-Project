# Workflow Designer

A comprehensive visual workflow builder for the AI Agent Orchestration Platform using React Flow.

## Features

### Visual Workflow Builder
- **Drag-and-drop interface**: Create workflows by dragging nodes from the toolbox
- **Node types**: Agent, Decision, Action, Input, Output
- **Custom node components**: Each node type has distinct visual styling
- **Zoom and pan**: Navigate large workflows with controls and mini-map
- **Grid snapping**: Align nodes to grid for clean layouts

### Workflow Management
- **Node configuration**: Edit properties of each node type
- **Edge connections**: Connect nodes with configurable data flow
- **Validation**: Check for errors (cycles, disconnected nodes, missing start/end)
- **Real-time simulation**: Preview workflow execution
- **Save/Load**: Persist workflows to backend API

### Integration
- **Backend API**: Connect to existing workflow management endpoints
- **Agent integration**: Link to existing agent management system
- **Tool execution**: Support for built-in tools (calculator, HTTP request, etc.)
- **Conditional logic**: Support for decision nodes with conditions

### User Experience
- **Properties panel**: Side panel for node configuration
- **Toolbox**: Quick access to all node types
- **Tooltips**: Hover information for nodes and buttons
- **Keyboard shortcuts**: Standard editing operations
- **Responsive design**: Works on desktop and tablet

## Node Types

### Agent Nodes
- **Purpose**: Execute AI agents
- **Configuration**: Agent selection, tool permissions
- **Visual**: Blue themed with circular icon

### Decision Nodes
- **Purpose**: Conditional branching logic
- **Configuration**: Condition expression
- **Visual**: Yellow themed with circular icon

### Action Nodes
- **Purpose**: Execute tools and actions
- **Configuration**: Tool selection
- **Visual**: Purple themed with circular icon

### Input Nodes
- **Purpose**: Starting point of workflows
- **Configuration**: Input value/description
- **Visual**: Green themed with circular icon

### Output Nodes
- **Purpose**: End point of workflows
- **Configuration**: Output value/description
- **Visual**: Red themed with circular icon

## Technical Implementation

### React Flow Integration
- Uses React Flow library for canvas and node management
- Custom node types extending React Flow's NodeProps interface
- Full control over node styling and behavior

### State Management
- Local state for workflow data (nodes, edges)
- React Flow's useNodesState and useEdgesState hooks
- Selected node tracking for property panel

### API Integration
- Mock data for initial implementation
- REST API endpoints for workflow CRUD operations
- WebSocket events for real-time updates (future)

### Styling
- Tailwind CSS with shadcn/ui components
- Custom CSS for node styling
- Responsive design principles

## API Endpoints

### Workflows
- `GET /api/v1/workflows` - List workflows
- `GET /api/v1/workflows/:id` - Get workflow details
- `PUT /api/v1/workflows/:id` - Update workflow

### Agents
- `GET /api/v1/agents` - List available agents
- `GET /api/v1/agents/:id` - Get agent details

## Future Enhancements

### Advanced Features
- Multi-agent coordination
- Parallel execution
- Error handling and retries
- Performance metrics
- Cost tracking

### User Experience
- Workflow templates
- Import/export functionality
- Collaboration features
- Version control

### Integration
- External API connectors
- Database integrations
- Third-party service integrations
- Real-time collaboration

## Development

### Setup
1. Install dependencies: `npm install`
2. Run development server: `npm run dev`
3. Access at: `http://localhost:3000`

### Building
1. Create new node components in `workflow-nodes/` directory
2. Add to nodeTypes export in workflow-designer.tsx
3. Update toolbox and properties panel as needed

### Testing
- Unit tests for node components
- Integration tests for workflow execution
- E2E tests for user workflows
# Workflow Node Components

This directory contains the custom node components for the React Flow workflow designer.

## Node Types

### AgentNode
- **Purpose**: Represents an AI agent in the workflow
- **Color**: Blue theme
- **Icon**: Blue circle
- **Properties**: Agent selection, tool permissions

### DecisionNode
- **Purpose**: Conditional logic node for branching workflows
- **Color**: Yellow theme
- **Icon**: Yellow circle
- **Properties**: Condition expression

### ActionNode
- **Purpose**: Tool execution node for performing actions
- **Color**: Purple theme
- **Icon**: Purple circle
- **Properties**: Tool selection

### InputNode
- **Purpose**: Starting point of workflows, receives user input
- **Color**: Green theme
- **Icon**: Green circle
- **Properties**: Input value/description

### OutputNode
- **Purpose**: End point of workflows, produces final output
- **Color**: Red theme
- **Icon**: Red circle
- **Properties**: Output value/description

## Usage

Each node component implements the `NodeProps<T>` interface from React Flow and includes:

- `data`: Node data with id, name, type, and position
- `selected`: Boolean indicating if node is selected
- `onSelect`: Callback when node is clicked

## Integration

The nodes are integrated with the main workflow designer through the `nodeTypes` export, which maps node type names to their corresponding components.
import { NextRequest, NextResponse } from 'next/server'

const mockWorkflow = {
  id: '1',
  name: 'Content Generation Pipeline',
  description: 'Automated content creation workflow',
  status: 'active',
  nodes: [
    {
      id: '1',
      type: 'input',
      position: { x: 100, y: 100 },
      data: { id: '1', name: 'Input', type: 'input', value: 'User input' }
    },
    {
      id: '2',
      type: 'agent',
      position: { x: 400, y: 100 },
      data: { id: '2', name: 'Content Writer', type: 'agent', agentId: '1' }
    },
    {
      id: '3',
      type: 'action',
      position: { x: 700, y: 100 },
      data: { id: '3', name: 'Publish Content', type: 'action', tool: 'http_request' }
    },
    {
      id: '4',
      type: 'output',
      position: { x: 1000, y: 100 },
      data: { id: '4', name: 'Output', type: 'output', value: 'Published content' }
    }
  ],
  edges: [
    { id: 'e1-2', source: '1', target: '2' },
    { id: 'e2-3', source: '2', target: '3' },
    { id: 'e3-4', source: '3', target: '4' }
  ],
  triggers: ['schedule', 'webhook'],
  created_at: '2024-01-20T08:30:00Z',
  updated_at: '2024-01-22T14:45:00Z'
}

export async function GET(request: NextRequest) {
  try {
    const id = request.nextUrl.searchParams.get('id')

    if (!id) {
      return NextResponse.json(
        { error: 'Workflow ID is required' },
        { status: 400 }
      )
    }

    // Return mock workflow for now
    return NextResponse.json(mockWorkflow)
  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}

export async function PUT(request: NextRequest) {
  try {
    const id = request.nextUrl.searchParams.get('id')

    if (!id) {
      return NextResponse.json(
        { error: 'Workflow ID is required' },
        { status: 400 }
      )
    }

    const body = await request.json()

    // Validate workflow data
    if (!body.name || !body.nodes || !body.edges) {
      return NextResponse.json(
        { error: 'Invalid workflow data' },
        { status: 400 }
      )
    }

    // Mock save - in real implementation, save to database
    console.log('Saving workflow:', body)

    return NextResponse.json({
      ...mockWorkflow,
      ...body,
      id: id,
      updated_at: new Date().toISOString()
    })
  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
import { NextRequest, NextResponse } from 'next/server'

const mockTasks = [
  {
    id: '1',
    workflow_id: '1',
    name: 'Generate Blog Post',
    status: 'completed',
    agent_id: '1',
    progress: 100,
    result: {
      content: 'Blog post content generated successfully',
      metadata: {
        word_count: 850,
        sentiment: 'positive',
        topics: ['technology', 'ai', 'development']
      }
    },
    created_at: '2024-01-22T10:00:00Z',
    updated_at: '2024-01-22T10:15:00Z'
  },
  {
    id: '2',
    workflow_id: '2',
    name: 'Process Customer Data',
    status: 'running',
    agent_id: '3',
    progress: 45,
    result: null,
    created_at: '2024-01-22T11:00:00Z',
    updated_at: '2024-01-22T11:27:00Z'
  },
  {
    id: '3',
    workflow_id: '3',
    name: 'Analyze Customer Feedback',
    status: 'pending',
    agent_id: '1',
    progress: 0,
    result: null,
    created_at: '2024-01-22T12:00:00Z',
    updated_at: '2024-01-22T12:00:00Z'
  }
]

export async function GET(request: NextRequest) {
  try {
    const workflowId = request.nextUrl.searchParams.get('workflow_id')
    const status = request.nextUrl.searchParams.get('status')
    const page = parseInt(request.nextUrl.searchParams.get('page') || '1')
    const limit = parseInt(request.nextUrl.searchParams.get('limit') || '10')

    let results = mockTasks

    if (workflowId) {
      results = results.filter(task => task.workflow_id === workflowId)
    }

    if (status) {
      results = results.filter(task => task.status === status)
    }

    const total = results.length
    const startIndex = (page - 1) * limit
    const endIndex = startIndex + limit
    const paginatedResults = results.slice(startIndex, endIndex)

    return NextResponse.json({
      tasks: paginatedResults,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit)
      }
    })
  } catch (error) {
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    )
  }
}
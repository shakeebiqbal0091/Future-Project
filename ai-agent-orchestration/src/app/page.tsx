"use client"

import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from './components/ui/card'
import { Button } from './components/ui/button'
import { Badge } from './components/ui/badge'
import { WorkflowDesigner } from './components/workflow-designer'
import { useRouter } from 'next/navigation'

export default function HomePage() {
  const router = useRouter()
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null)

  const workflows = [
    { id: '1', name: 'Content Generation Pipeline', description: 'Automated content creation workflow', status: 'active' },
    { id: '2', name: 'Data Analysis Workflow', description: 'Automated data processing and analysis', status: 'active' },
    { id: '3', name: 'Customer Support Automation', description: 'Automated customer support workflow', status: 'inactive' },
    { id: '4', name: 'Sales Pipeline Automation', description: 'Automated sales workflow', status: 'active' }
  ]

  const handleCreateWorkflow = () => {
    setSelectedWorkflow(null)
  }

  const handleEditWorkflow = (workflowId: string) => {
    setSelectedWorkflow(workflowId)
  }

  if (selectedWorkflow !== null) {
    return <WorkflowDesigner workflowId={selectedWorkflow} />
  }

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Header */}
      <header className="bg-background/80 backdrop-blur-sm border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-foreground">Workflow Designer</h1>
            <p className="text-muted-foreground mt-1">
              Build and manage AI agent workflows visually
            </p>
          </div>
          <Button
            onClick={handleCreateWorkflow}
            variant="default"
            className="bg-primary text-primary-foreground hover:bg-primary/90"
          >
            + Create New Workflow
          </Button>
        </div>
      </header>

      {/* Main Content */}
      <main className="px-6 py-8">
        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
          <div className="bg-surface rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Total Workflows</p>
                <p className="text-2xl font-bold text-foreground">{workflows.length}</p>
              </div>
              <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                Active
              </Badge>
            </div>
          </div>

          <div className="bg-surface rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Active Workflows</p>
                <p className="text-2xl font-bold text-foreground">{workflows.filter(w => w.status === 'active').length}</p>
              </div>
              <Badge variant="secondary" className="bg-green-100 text-green-800">
                {workflows.filter(w => w.status === 'active').length}
              </Badge>
            </div>
          </div>

          <div className="bg-surface rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Agents Used</p>
                <p className="text-2xl font-bold text-foreground">15</p>
              </div>
              <Badge variant="secondary" className="bg-purple-100 text-purple-800">
                Connected
              </Badge>
            </div>
          </div>

          <div className="bg-surface rounded-lg p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">Recent Runs</p>
                <p className="text-2xl font-bold text-foreground">42</p>
              </div>
              <Badge variant="secondary" className="bg-orange-100 text-orange-800">
                Today
              </Badge>
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          <Card className="p-6">
            <CardHeader>
              <CardTitle className="flex items-center">
                <svg className="w-5 h-5 mr-2 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Quick Actions
              </CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-3">
              <Button
                variant="outline"
                className="w-full"
                onClick={handleCreateWorkflow}
              >
                Create Workflow
              </Button>
              <Button
                variant="outline"
                className="w-full"
                onClick={() => router.push('/agents')}
              >
                Manage Agents
              </Button>
              <Button
                variant="outline"
                className="w-full"
                onClick={() => router.push('/analytics')}
              >
                View Analytics
              </Button>
              <Button
                variant="outline"
                className="w-full"
                onClick={() => router.push('/integrations')}
              >
                Integrations
              </Button>
            </CardContent>
          </Card>

          <Card className="p-6">
            <CardHeader>
              <CardTitle className="flex items-center">
                <svg className="w-5 h-5 mr-2 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Recent Workflows
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {workflows.map(workflow => (
                  <div key={workflow.id} className="flex items-center justify-between">
                    <div>
                      <p className="font-medium text-foreground">{workflow.name}</p>
                      <p className="text-sm text-muted-foreground">{workflow.description}</p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEditWorkflow(workflow.id)}
                    >
                      Edit
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card className="p-6">
            <CardHeader>
              <CardTitle className="flex items-center">
                <svg className="w-5 h-5 mr-2 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Getting Started
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  Welcome to the Workflow Designer! Create your first AI agent workflow by clicking the "Create New Workflow" button.
                </p>
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleCreateWorkflow}
                    className="w-full"
                  >
                    Get Started
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => router.push('/docs')}
                    className="w-full"
                  >
                    View Docs
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recent Activity */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Activity</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-start space-x-3">
                <div className="w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                <div className="flex-1">
                  <p className="font-medium text-foreground">Workflow created</p>
                  <p className="text-sm text-muted-foreground">Content Generation Pipeline created successfully</p>
                  <p className="text-xs text-muted-foreground">2 hours ago</p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <div className="w-2 h-2 bg-green-500 rounded-full mt-2"></div>
                <div className="flex-1">
                  <p className="font-medium text-foreground">Workflow executed</p>
                  <p className="text-sm text-muted-foreground">Data Analysis Workflow completed with 98% success rate</p>
                  <p className="text-xs text-muted-foreground">4 hours ago</p>
                </div>
              </div>

              <div className="flex items-start space-x-3">
                <div className="w-2 h-2 bg-purple-500 rounded-full mt-2"></div>
                <div className="flex-1">
                  <p className="font-medium text-foreground">Agent updated</p>
                  <p className="text-sm text-muted-foreground">Sales Assistant agent configuration updated</p>
                  <p className="text-xs text-muted-foreground">6 hours ago</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </main>
    </div>
  )
}
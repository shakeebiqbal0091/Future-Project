# Database Initialization Script for AI Agent Orchestration Platform
-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "postgis";

-- Create schemas
CREATE SCHEMA IF NOT EXISTS ai_orchestration;
CREATE SCHEMA IF NOT EXISTS analytics;
CREATE SCHEMA IF NOT EXISTS audit;

-- Set default search path
ALTER ROLE postgres SET search_path = ai_orchestration, analytics, audit, public;

-- Create necessary tables
CREATE TABLE IF NOT EXISTS ai_orchestration.agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(100) NOT NULL,
    config JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_orchestration.workflows (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    agent_ids UUID[] NOT NULL,
    status VARCHAR(50) DEFAULT 'inactive',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ai_orchestration.executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_id UUID REFERENCES ai_orchestration.workflows(id),
    agent_executions JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    result JSONB,
    error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_agents_name ON ai_orchestration.agents(name);
CREATE INDEX idx_workflows_name ON ai_orchestration.workflows(name);
CREATE INDEX idx_executions_workflow_id ON ai_orchestration.executions(workflow_id);
CREATE INDEX idx_executions_status ON ai_orchestration.executions(status);

-- Create views for analytics
CREATE OR REPLACE VIEW analytics.workflow_summary AS
SELECT
    w.name,
    COUNT(e.id) as execution_count,
    AVG(EXTRACT(EPOCH FROM (e.completed_at - e.created_at))) as avg_execution_time,
    MAX(e.created_at) as last_execution
FROM ai_orchestration.workflows w
LEFT JOIN ai_orchestration.executions e ON w.id = e.workflow_id
GROUP BY w.name;

-- Insert default data
INSERT INTO ai_orchestration.agents (name, description, type, config) VALUES
('Default Agent', 'Basic agent for simple tasks', 'basic', '{"max_concurrency": 1}'),
('Data Processing Agent', 'Agent specialized in data processing', 'data', '{"max_concurrency": 3}'),
('Analysis Agent', 'Agent for complex analysis', 'analysis', '{"max_concurrency": 2}');
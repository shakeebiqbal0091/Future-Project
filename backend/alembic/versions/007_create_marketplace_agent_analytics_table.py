from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Create marketplace agent analytics table
    op.create_table(
        'marketplace_agent_analytics',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('marketplace_agent_id', sa.UUID(as_uuid=True), sa.ForeignKey('marketplace_agents.id'), nullable=False),
        sa.Column('date', sa.Date, nullable=False),
        sa.Column('views', sa.Integer, nullable=False, default=0),
        sa.Column('unique_views', sa.Integer, nullable=False, default=0),
        sa.Column('installs', sa.Integer, nullable=False, default=0),
        sa.Column('uninstalls', sa.Integer, nullable=False, default=0),
        sa.Column('active_users', sa.Integer, nullable=False, default=0),
        sa.Column('usage_hours', sa.Numeric(10, 2), nullable=False, default=0.0),
        sa.Column('success_rate', sa.Numeric(5, 4), nullable=False, default=0.0),  # 0.0000 to 1.0000
        sa.Column('avg_execution_time_ms', sa.Integer, nullable=False, default=0),
        sa.Column('tokens_used', sa.Integer, nullable=False, default=0),
        sa.Column('cost_usd', sa.Numeric(10, 4), nullable=False, default=0.0000),
    )

    # Create indexes
    op.create_index('idx_analytics_agent_id', 'marketplace_agent_analytics', ['marketplace_agent_id'])
    op.create_index('idx_analytics_date', 'marketplace_agent_analytics', ['date'])
    op.create_index('idx_analytics_agent_date', 'marketplace_agent_analytics', ['marketplace_agent_id', 'date'])
    op.create_index('idx_analytics_installs', 'marketplace_agent_analytics', ['installs'])
    op.create_index('idx_analytics_views', 'marketplace_agent_analytics', ['views'])

    # Create foreign key constraint
    op.create_foreign_key('fk_analytics_agent', 'marketplace_agent_analytics', 'marketplace_agents', ['marketplace_agent_id'], ['id'])

def downgrade():
    op.drop_table('marketplace_agent_analytics')
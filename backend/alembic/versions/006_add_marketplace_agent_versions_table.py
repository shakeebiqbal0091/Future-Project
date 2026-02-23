from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Create marketplace agent versions table
    op.create_table(
        'marketplace_agent_versions',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('marketplace_agent_id', sa.UUID(as_uuid=True), sa.ForeignKey('marketplace_agents.id'), nullable=False),
        sa.Column('version', sa.Integer, nullable=False),
        sa.Column('config', postgresql.JSONB, nullable=False),
        sa.Column('released_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('changelog', sa.Text, nullable=True),
        sa.Column('is_stable', sa.Boolean, nullable=False, default=False),
        sa.Column('is_deprecated', sa.Boolean, nullable=False, default=False),
        sa.Column('min_agent_version', sa.String, nullable=True),  # Minimum compatible agent version
        sa.Column('release_notes', sa.Text, nullable=True),
    )

    # Create indexes
    op.create_index('idx_agent_versions_agent_id', 'marketplace_agent_versions', ['marketplace_agent_id'])
    op.create_index('idx_agent_versions_version', 'marketplace_agent_versions', ['version'])
    op.create_index('idx_agent_versions_stable', 'marketplace_agent_versions', ['is_stable'])
    op.create_index('idx_agent_versions_deprecated', 'marketplace_agent_versions', ['is_deprecated'])
    op.create_index('idx_agent_versions_released', 'marketplace_agent_versions', ['released_at'])

    # Create foreign key constraint
    op.create_foreign_key('fk_agent_versions_agent', 'marketplace_agent_versions', 'marketplace_agents', ['marketplace_agent_id'], ['id'])

def downgrade():
    op.drop_table('marketplace_agent_versions')
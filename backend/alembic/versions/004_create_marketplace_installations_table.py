from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Create installations table to track agent installations
    op.create_table(
        'marketplace_installations',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('marketplace_agent_id', sa.UUID(as_uuid=True), sa.ForeignKey('marketplace_agents.id'), nullable=False),
        sa.Column('organization_id', sa.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('installed_by', sa.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('installed_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('installed_version', sa.Integer, nullable=False),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('last_used_at', sa.DateTime(timezone=True)),
        sa.Column('usage_count', sa.Integer, nullable=False, default=0),
        sa.Column('customizations', postgresql.JSONB, nullable=True),  # Store any organization-specific customizations
    )

    # Create indexes
    op.create_index('idx_installations_agent_id', 'marketplace_installations', ['marketplace_agent_id'])
    op.create_index('idx_installations_org_id', 'marketplace_installations', ['organization_id'])
    op.create_index('idx_installations_user_id', 'marketplace_installations', ['installed_by'])
    op.create_index('idx_installations_active', 'marketplace_installations', ['is_active'])
    op.create_index('idx_installations_last_used', 'marketplace_installations', ['last_used_at'])

    # Create foreign key constraints
    op.create_foreign_key('fk_installations_agent', 'marketplace_installations', 'marketplace_agents', ['marketplace_agent_id'], ['id'])
    op.create_foreign_key('fk_installations_org', 'marketplace_installations', 'organizations', ['organization_id'], ['id'])
    op.create_foreign_key('fk_installations_user', 'marketplace_installations', 'users', ['installed_by'], ['id'])

def downgrade():
    op.drop_table('marketplace_installations')
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Add new fields to agents table for marketplace functionality
    op.add_column('agents', sa.Column('is_marketplace', sa.Boolean, nullable=False, default=False))
    op.add_column('agents', sa.Column('marketplace_id', sa.UUID, nullable=True))
    op.add_column('agents', sa.Column('marketplace_rating', sa.Numeric(3, 2), nullable=True))
    op.add_column('agents', sa.Column('marketplace_reviews', sa.Integer, nullable=True, default=0))
    op.add_column('agents', sa.Column('marketplace_price', sa.Numeric(10, 2), nullable=True, default=0.0))
    op.add_column('agents', sa.Column('marketplace_version', sa.Integer, nullable=True))

    # Create indexes
    op.create_index('idx_agents_marketplace', 'agents', ['is_marketplace'])
    op.create_index('idx_agents_marketplace_id', 'agents', ['marketplace_id'])

def downgrade():
    op.drop_column('agents', 'is_marketplace')
    op.drop_column('agents', 'marketplace_id')
    op.drop_column('agents', 'marketplace_rating')
    op.drop_column('agents', 'marketplace_reviews')
    op.drop_column('agents', 'marketplace_price')
    op.drop_column('agents', 'marketplace_version')
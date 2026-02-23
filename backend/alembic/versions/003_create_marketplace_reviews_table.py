from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Create reviews table for marketplace agents
    op.create_table(
        'marketplace_reviews',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('marketplace_agent_id', sa.UUID(as_uuid=True), sa.ForeignKey('marketplace_agents.id'), nullable=False),
        sa.Column('user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('rating', sa.Integer, nullable=False, default=0),  # 1-5 stars
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('comment', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),
        sa.Column('is_verified_purchase', sa.Boolean, nullable=False, default=False),
        sa.Column('is_featured', sa.Boolean, nullable=False, default=False),
        sa.Column('helpful_count', sa.Integer, nullable=False, default=0),
        sa.Column('not_helpful_count', sa.Integer, nullable=False, default=0),
    )

    # Create indexes
    op.create_index('idx_reviews_agent_id', 'marketplace_reviews', ['marketplace_agent_id'])
    op.create_index('idx_reviews_user_id', 'marketplace_reviews', ['user_id'])
    op.create_index('idx_reviews_rating', 'marketplace_reviews', ['rating'])
    op.create_index('idx_reviews_verified', 'marketplace_reviews', ['is_verified_purchase'])
    op.create_index('idx_reviews_featured', 'marketplace_reviews', ['is_featured'])
    op.create_index('idx_reviews_created', 'marketplace_reviews', ['created_at'])

    # Create foreign key constraints
    op.create_foreign_key('fk_reviews_agent', 'marketplace_reviews', 'marketplace_agents', ['marketplace_agent_id'], ['id'])
    op.create_foreign_key('fk_reviews_user', 'marketplace_reviews', 'users', ['user_id'], ['id'])

def downgrade():
    op.drop_table('marketplace_reviews')
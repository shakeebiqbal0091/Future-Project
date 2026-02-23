from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # Add marketplace_agents table to store pre-built agents
    op.create_table(
        'marketplace_agents',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String, nullable=False),
        sa.Column('description', sa.Text, nullable=False),
        sa.Column('category', sa.String, nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=False, default=0.0),
        sa.Column('rating', sa.Numeric(3, 2), nullable=False, default=0.0),
        sa.Column('reviews', sa.Integer, nullable=False, default=0),
        sa.Column('author', sa.String, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('version', sa.Integer, nullable=False, default=1),
        sa.Column('compatible', sa.Boolean, nullable=False, default=True),
        sa.Column('is_featured', sa.Boolean, nullable=False, default=False),
        sa.Column('tools', postgresql.ARRAY(sa.String), nullable=False, default=[]),
        sa.Column('requirements', postgresql.ARRAY(sa.String), nullable=False, default=[]),
        sa.Column('tags', postgresql.ARRAY(sa.String), nullable=False, default=[]),
        sa.Column('is_public', sa.Boolean, nullable=False, default=True),
        sa.Column('is_active', sa.Boolean, nullable=False, default=True),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),
        sa.Column('tags_vector', postgresql.TSVECTOR, nullable=True),
    )

    # Create indexes for better query performance
    op.create_index('idx_marketplace_name', 'marketplace_agents', ['name'])
    op.create_index('idx_marketplace_category', 'marketplace_agents', ['category'])
    op.create_index('idx_marketplace_author', 'marketplace_agents', ['author'])
    op.create_index('idx_marketplace_rating', 'marketplace_agents', ['rating'])
    op.create_index('idx_marketplace_featured', 'marketplace_agents', ['is_featured'])
    op.create_index('idx_marketplace_active', 'marketplace_agents', ['is_active'])
    op.create_index('idx_marketplace_created', 'marketplace_agents', ['created_at'])

    # Create GIN index for tags and full-text search
    op.create_index('idx_marketplace_tags', 'marketplace_agents', ['tags'], postgresql_using='gin')
    op.create_index('idx_marketplace_tags_vector', 'marketplace_agents', ['tags_vector'], postgresql_using='gin')

    # Create function for updating tags vector
    op.execute("")
    op.execute("CREATE OR REPLACE FUNCTION update_tags_vector() RETURNS trigger AS $$")
    op.execute("BEGIN")
    op.execute("    NEW.tags_vector := to_tsvector('english', array_to_string(NEW.tags, ' '));")
    op.execute("    RETURN NEW;")
    op.execute("END;")
    op.execute("$$ LANGUAGE plpgsql;")

    # Create trigger for tags vector update
    op.execute("CREATE TRIGGER marketplace_tags_vector_update")
    op.execute("BEFORE INSERT OR UPDATE ON marketplace_agents")
    op.execute("FOR EACH ROW EXECUTE FUNCTION update_tags_vector();")

def downgrade():
    op.drop_table('marketplace_agents')
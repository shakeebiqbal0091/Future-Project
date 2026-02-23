from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('username', sa.String, nullable=False, unique=True, index=True),
        sa.Column('email', sa.String, nullable=False, unique=True, index=True),
        sa.Column('hashed_password', sa.String, nullable=False),
        sa.Column('full_name', sa.String),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('is_superuser', sa.Boolean, default=False),
        sa.Column('email_verified', sa.Boolean, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()')),
    )

    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.UUID(as_uuid=True), primary_key=True, default=sa.text('gen_random_uuid()')),
        sa.Column('key', sa.String, nullable=False, unique=True, index=True),
        sa.Column('user_id', sa.UUID, sa.ForeignKey('users.id'), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('expires_at', sa.DateTime(timezone=True)),
        sa.Column('last_used_at', sa.DateTime(timezone=True)),
    )

    # Create indexes
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_username', 'users', ['username'])
    op.create_index('idx_api_keys_key', 'api_keys', ['key'])
    op.create_index('idx_api_keys_user_id', 'api_keys', ['user_id'])

def downgrade():
    op.drop_table('api_keys')
    op.drop_table('users')
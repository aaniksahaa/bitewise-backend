"""add intakes, fitness_plans, posts, comments, conversations, messages tables

Revision ID: add_intakes_fitness_posts_comments_conversations_messages
Revises: add_ingredients_and_dishes_tables
Create Date: 2024-05-26 22:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as psql

# revision identifiers, used by Alembic.
revision = 'add_intakes_fitness_posts_comments_conversations_messages'
down_revision = 'add_ingredients_and_dishes_tables'
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'intakes',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('dish_id', sa.BigInteger(), sa.ForeignKey('dishes.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('intake_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('portion_size', sa.Numeric(5, 2), server_default='1.0'),
        sa.Column('water_ml', sa.Integer()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'fitness_plans',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('goal_type', sa.String(length=50), nullable=False),
        sa.Column('target_weight_kg', sa.Numeric(5, 2)),
        sa.Column('target_calories_per_day', sa.Integer()),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('suggestions', psql.JSONB),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'posts',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('dish_id', sa.BigInteger(), sa.ForeignKey('dishes.id', ondelete='SET NULL'), nullable=True),
        sa.Column('tags', psql.ARRAY(sa.Text)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'comments',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('post_id', sa.BigInteger(), sa.ForeignKey('posts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
    )

    op.create_table(
        'conversations',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=255)),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('metadata', psql.JSONB),
        sa.CheckConstraint("status IN ('active', 'archived', 'deleted')", name='valid_status'),
    )

    op.create_table(
        'messages',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('conversation_id', sa.BigInteger(), sa.ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('is_user_message', sa.Boolean(), nullable=False),
        sa.Column('llm_model_id', sa.BigInteger(), sa.ForeignKey('llm_models.id', ondelete='SET NULL'), nullable=True),
        sa.Column('input_tokens', sa.Integer()),
        sa.Column('output_tokens', sa.Integer()),
        sa.Column('parent_message_id', sa.BigInteger(), sa.ForeignKey('messages.id', ondelete='SET NULL'), nullable=True),
        sa.Column('message_type', sa.String(length=50), nullable=False, server_default='text'),
        sa.Column('attachments', psql.JSONB),
        sa.Column('reactions', psql.JSONB),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='sent'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('metadata', psql.JSONB),
        sa.CheckConstraint("message_type IN ('text', 'image', 'file', 'system')", name='valid_message_type'),
        sa.CheckConstraint("status IN ('sent', 'delivered', 'read', 'edited', 'deleted')", name='valid_status'),
    )

def downgrade():
    op.drop_table('messages')
    op.drop_table('conversations')
    op.drop_table('comments')
    op.drop_table('posts')
    op.drop_table('fitness_plans')
    op.drop_table('intakes') 
"""4.2.4 notifications and audit tables

Revision ID: 37108ea71cca
Revises: 1a56dc8b2ff7
Create Date: 2026-10-26 02:34:15.788451

Also installs the append-only trigger for ``audit_logs``: UPDATE/DELETE raise an
error at the database level so history cannot be altered even by an application
bug. Implemented per dialect (PL/pgSQL on PostgreSQL, RAISE(ABORT) on SQLite).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '37108ea71cca'
down_revision: Union[str, None] = '1a56dc8b2ff7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_audit_trigger() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION audit_logs_block_modifications()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'audit_logs is append-only';
            END;
            $$ LANGUAGE plpgsql;
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_audit_logs_append_only
            BEFORE UPDATE OR DELETE ON audit_logs
            FOR EACH ROW EXECUTE FUNCTION audit_logs_block_modifications();
            """
        )
    elif dialect == "sqlite":
        op.execute(
            """
            CREATE TRIGGER trg_audit_logs_no_update
            BEFORE UPDATE ON audit_logs
            BEGIN
                SELECT RAISE(ABORT, 'audit_logs is append-only');
            END;
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_audit_logs_no_delete
            BEFORE DELETE ON audit_logs
            BEGIN
                SELECT RAISE(ABORT, 'audit_logs is append-only');
            END;
            """
        )


def _drop_audit_trigger() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_append_only ON audit_logs;")
        op.execute("DROP FUNCTION IF EXISTS audit_logs_block_modifications();")
    elif dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_no_update;")
        op.execute("DROP TRIGGER IF EXISTS trg_audit_logs_no_delete;")


def upgrade() -> None:
    op.create_table(
        'audit_logs',
        sa.Column('org_id', sa.Uuid(), nullable=True),
        sa.Column('actor_id', sa.Uuid(), nullable=True),
        sa.Column('action', sa.String(length=80), nullable=False),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.Uuid(), nullable=True),
        sa.Column('metadata', sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), 'postgresql'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_audit_logs_org_id'), ['org_id'], unique=False)
        batch_op.create_index('ix_audit_org_action', ['org_id', 'action'], unique=False)
        batch_op.create_index('ix_audit_org_created', ['org_id', 'created_at'], unique=False)

    op.create_table(
        'notifications',
        sa.Column('org_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('type', sa.Enum('task_assigned', 'task_status_changed', 'approval_requested', 'approval_decided', 'task_due_soon', 'task_overdue', name='notification_type', native_enum=False, length=40), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('resource_type', sa.String(length=50), nullable=True),
        sa.Column('resource_id', sa.Uuid(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.create_index('ix_notification_org_user', ['org_id', 'user_id'], unique=False)
        batch_op.create_index('ix_notification_user_read_created', ['user_id', 'is_read', 'created_at'], unique=False)
        batch_op.create_index(batch_op.f('ix_notifications_org_id'), ['org_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_notifications_user_id'), ['user_id'], unique=False)

    # Append-only enforcement at the database level.
    _create_audit_trigger()


def downgrade() -> None:
    _drop_audit_trigger()

    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_notifications_user_id'))
        batch_op.drop_index(batch_op.f('ix_notifications_org_id'))
        batch_op.drop_index('ix_notification_user_read_created')
        batch_op.drop_index('ix_notification_org_user')

    op.drop_table('notifications')
    with op.batch_alter_table('audit_logs', schema=None) as batch_op:
        batch_op.drop_index('ix_audit_org_created')
        batch_op.drop_index('ix_audit_org_action')
        batch_op.drop_index(batch_op.f('ix_audit_logs_org_id'))

    op.drop_table('audit_logs')

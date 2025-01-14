"""Add template project to settings

Revision ID: add_template_project
Revises: 
Create Date: 2024-12-15 01:10:43.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_template_project'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('settings', sa.Column('template_project_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'settings', 'project', ['template_project_id'], ['id'])

def downgrade():
    op.drop_constraint(None, 'settings', type_='foreignkey')
    op.drop_column('settings', 'template_project_id')

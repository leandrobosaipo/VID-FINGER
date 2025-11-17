"""Make files.analysis_id nullable to break circular FK insertion."""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b1c2d3e4f5a6"
down_revision = "a34cb10e4c93"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Permitir que files.analysis_id seja nulo na criação do arquivo."""
    op.alter_column(
        "files",
        "analysis_id",
        existing_type=sa.UUID(),
        nullable=True,
    )


def downgrade() -> None:
    """Reverter para NOT NULL (pode falhar se houver registros nulos)."""
    op.alter_column(
        "files",
        "analysis_id",
        existing_type=sa.UUID(),
        nullable=False,
    )


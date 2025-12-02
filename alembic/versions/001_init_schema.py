# alembic/versions/001_init_schema.py
"""Initial schema

Revision ID: 001_init_schema
Revises: 
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_init_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create all tables."""
    
    # Seasons
    op.create_table('seasons',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('year')
    )
    op.create_index('ix_seasons_year', 'seasons', ['year'])
    
    # Races
    op.create_table('races',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('season_id', sa.Integer(), nullable=False),
        sa.Column('round', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('circuit_name', sa.String(length=200), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=False),
        sa.Column('date', sa.DateTime(), nullable=False),
        sa.Column('total_laps', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['season_id'], ['seasons.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('season_id', 'round', name='uq_season_round')
    )
    op.create_index('ix_races_season_id', 'races', ['season_id'])
    op.create_index('ix_races_season_round', 'races', ['season_id', 'round'])
    
    # Sessions
    op.create_table('sessions',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('session_type', sa.String(length=20), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=True),
        sa.Column('end_time', sa.DateTime(), nullable=True),
        sa.Column('fastf1_identifier', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['race_id'], ['races.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('race_id', 'session_type', name='uq_race_session_type')
    )
    op.create_index('ix_sessions_race_id', 'sessions', ['race_id'])
    op.create_index('ix_sessions_race_type', 'sessions', ['race_id', 'session_type'])
    
    # Teams
    op.create_table('teams',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('short_name', sa.String(length=50), nullable=False),
        sa.Column('color_hex', sa.String(length=7), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_teams_name', 'teams', ['name'])
    
    # Drivers
    op.create_table('drivers',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(length=3), nullable=False),
        sa.Column('full_name', sa.String(length=100), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('permanent_number', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index('ix_drivers_code', 'drivers', ['code'])
    
    # Driver Session Results
    op.create_table('driver_session_results',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('team_id', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('grid_position', sa.Integer(), nullable=True),
        sa.Column('points', sa.Float(), nullable=True),
        sa.Column('final_status', sa.String(length=50), nullable=False),
        sa.Column('total_race_time_sec', sa.Float(), nullable=True),
        sa.Column('time_text', sa.String(length=50), nullable=True),
        sa.Column('gap_to_winner_text', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id']),
        sa.ForeignKeyConstraint(['team_id'], ['teams.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'driver_id', name='uq_session_driver')
    )
    op.create_index('ix_results_session_id', 'driver_session_results', ['session_id'])
    op.create_index('ix_results_driver_id', 'driver_session_results', ['driver_id'])
    op.create_index('ix_results_team_id', 'driver_session_results', ['team_id'])
    op.create_index('ix_results_session_driver', 'driver_session_results', ['session_id', 'driver_id'])
    op.create_index('ix_results_position', 'driver_session_results', ['session_id', 'position'])
    
    # Laps
    op.create_table('laps',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('lap_number', sa.Integer(), nullable=False),
        sa.Column('lap_time_sec', sa.Float(), nullable=True),
        sa.Column('sector1_time_sec', sa.Float(), nullable=True),
        sa.Column('sector2_time_sec', sa.Float(), nullable=True),
        sa.Column('sector3_time_sec', sa.Float(), nullable=True),
        sa.Column('is_pit_lap', sa.Boolean(), nullable=False),
        sa.Column('tyre_compound', sa.String(length=20), nullable=True),
        sa.Column('tyre_life_laps', sa.Integer(), nullable=True),
        sa.Column('track_status', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_laps_session_id', 'laps', ['session_id'])
    op.create_index('ix_laps_driver_id', 'laps', ['driver_id'])
    op.create_index('ix_laps_session_driver_lap', 'laps', ['session_id', 'driver_id', 'lap_number'], unique=True)
    op.create_index('ix_laps_session_lap', 'laps', ['session_id', 'lap_number'])
    
    # Stints
    op.create_table('stints',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('stint_number', sa.Integer(), nullable=False),
        sa.Column('start_lap', sa.Integer(), nullable=False),
        sa.Column('end_lap', sa.Integer(), nullable=False),
        sa.Column('compound', sa.String(length=20), nullable=False),
        sa.Column('avg_lap_time_sec', sa.Float(), nullable=False),
        sa.Column('laps_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_stints_session_id', 'stints', ['session_id'])
    op.create_index('ix_stints_driver_id', 'stints', ['driver_id'])
    op.create_index('ix_stints_session_driver_stint', 'stints', ['session_id', 'driver_id', 'stint_number'], unique=True)
    op.create_index('ix_stints_session_driver', 'stints', ['session_id', 'driver_id'])
    
    # Telemetry Frames
    op.create_table('telemetry_frames',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('driver_id', sa.Integer(), nullable=False),
        sa.Column('t_rel_sec', sa.Float(), nullable=False),
        sa.Column('lap_number', sa.Integer(), nullable=False),
        sa.Column('x_norm', sa.Float(), nullable=False),
        sa.Column('y_norm', sa.Float(), nullable=False),
        sa.Column('speed_kph', sa.Float(), nullable=True),
        sa.Column('throttle', sa.Float(), nullable=True),
        sa.Column('brake', sa.Float(), nullable=True),
        sa.Column('gear', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['driver_id'], ['drivers.id']),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_telemetry_session_id', 'telemetry_frames', ['session_id'])
    op.create_index('ix_telemetry_driver_id', 'telemetry_frames', ['driver_id'])
    op.create_index('ix_telemetry_session_driver_time', 'telemetry_frames', ['session_id', 'driver_id', 't_rel_sec'])
    op.create_index('ix_telemetry_session_time', 'telemetry_frames', ['session_id', 't_rel_sec'])
    
    # Track Shape Points
    op.create_table('track_shape_points',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('x_norm', sa.Float(), nullable=False),
        sa.Column('y_norm', sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(['race_id'], ['races.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_track_shape_race_id', 'track_shape_points', ['race_id'])
    op.create_index('ix_track_shape_race_order', 'track_shape_points', ['race_id', 'order_index'], unique=True)


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table('track_shape_points')
    op.drop_table('telemetry_frames')
    op.drop_table('stints')
    op.drop_table('laps')
    op.drop_table('driver_session_results')
    op.drop_table('drivers')
    op.drop_table('teams')
    op.drop_table('sessions')
    op.drop_table('races')
    op.drop_table('seasons')
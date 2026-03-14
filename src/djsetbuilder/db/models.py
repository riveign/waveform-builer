"""SQLAlchemy models for the DJ library database."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    Float,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker
from sqlalchemy.pool import NullPool

from djsetbuilder.config import get_db_url

# Module-level singletons — initialized once per process
_engine = None
_SessionFactory = None
_schema_initialized = False


class Base(DeclarativeBase):
    pass


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True)
    rb_id = Column(String, unique=True)
    title = Column(String)
    artist = Column(String)
    album = Column(String)
    rb_genre = Column(String)
    dir_genre = Column(String)
    dir_energy = Column(String)
    bpm = Column(Float)
    key = Column(String)
    rating = Column(Integer)
    color = Column(String)
    comment = Column(Text)
    duration_sec = Column(Float)
    file_path = Column(String)
    file_hash = Column(String)
    date_added = Column(String)
    play_count = Column(Integer, default=0)
    release_year = Column(Integer)
    acquired_month = Column(String)
    playlist_tags = Column(Text)  # JSON list of playlist names this track belongs to
    last_synced = Column(String)
    energy_predicted = Column(String)   # Predicted energy tag from autotag classifier
    energy_confidence = Column(Float)   # Prediction confidence 0-1
    energy_source = Column(String)      # "manual", "auto", or "approved"

    audio_features = relationship(
        "AudioFeatures", back_populates="track", uselist=False, cascade="all, delete-orphan"
    )


class AudioFeatures(Base):
    __tablename__ = "audio_features"

    track_id = Column(Integer, ForeignKey("tracks.id"), primary_key=True)
    energy = Column(Float)
    danceability = Column(Float)
    loudness_lufs = Column(Float)
    spectral_centroid = Column(Float)
    spectral_complexity = Column(Float)
    mood_happy = Column(Float)
    mood_sad = Column(Float)
    mood_aggressive = Column(Float)
    mood_relaxed = Column(Float)
    ml_genre = Column(String)
    ml_genre_confidence = Column(Float)
    energy_intro = Column(Float)
    energy_body = Column(Float)
    energy_outro = Column(Float)
    mfcc_mean = Column(LargeBinary)
    mfcc_var = Column(LargeBinary)
    verified_bpm = Column(Float)
    verified_key = Column(String)
    analyzed_at = Column(String)
    # Waveform data for visualization
    waveform_overview = Column(LargeBinary)   # ~1000 float32 peak-downsampled RMS
    waveform_detail = Column(LargeBinary)     # ~10K float32 full RMS envelope
    waveform_sr = Column(Integer)             # Sample rate used (22050)
    waveform_hop = Column(Integer)            # Hop length used (512)
    beat_positions = Column(LargeBinary)      # float32 array of beat timestamps in seconds
    # Frequency band envelopes (4 bands × detail + overview)
    band_low = Column(LargeBinary)              # 20–250 Hz RMS detail
    band_midlow = Column(LargeBinary)           # 250–1000 Hz RMS detail
    band_midhigh = Column(LargeBinary)          # 1000–4000 Hz RMS detail
    band_high = Column(LargeBinary)             # 4000–11025 Hz RMS detail
    band_low_overview = Column(LargeBinary)     # 20–250 Hz RMS overview
    band_midlow_overview = Column(LargeBinary)  # 250–1000 Hz RMS overview
    band_midhigh_overview = Column(LargeBinary) # 1000–4000 Hz RMS overview
    band_high_overview = Column(LargeBinary)    # 4000–11025 Hz RMS overview

    track = relationship("Track", back_populates="audio_features")


class Set(Base):
    __tablename__ = "sets"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    created_at = Column(String, default=lambda: datetime.now().isoformat())
    duration_min = Column(Integer)
    energy_profile = Column(Text)  # JSON
    genre_filter = Column(Text)  # JSON

    tracks = relationship("SetTrack", back_populates="set_", cascade="all, delete-orphan")


class SetTrack(Base):
    __tablename__ = "set_tracks"

    set_id = Column(Integer, ForeignKey("sets.id"), primary_key=True)
    position = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey("tracks.id"))
    transition_score = Column(Float)

    set_ = relationship("Set", back_populates="tracks")
    track = relationship("Track")


class TransitionCue(Base):
    __tablename__ = "transition_cues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    set_id = Column(Integer, ForeignKey("sets.id", ondelete="CASCADE"), nullable=False)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    position = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    cue_type = Column(String, nullable=False, default="cue")
    start_sec = Column(Float, nullable=False)
    end_sec = Column(Float)
    hot_cue_num = Column(Integer, default=-1)
    color = Column(String)
    created_at = Column(String, default=lambda: datetime.now().isoformat())

    set_ = relationship("Set")
    track = relationship("Track")


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(get_db_url(), poolclass=NullPool)
    return _engine


def _init_schema():
    """Create tables once per process. Schema migrations handled by Alembic."""
    global _schema_initialized
    if _schema_initialized:
        return
    engine = get_engine()
    Base.metadata.create_all(engine)
    _schema_initialized = True


def get_session() -> Session:
    global _SessionFactory
    _init_schema()
    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine())
    return _SessionFactory()

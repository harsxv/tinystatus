from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Float, Text, inspect
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from .config import get_settings

settings = get_settings()

# Database connection
engine = create_engine(settings.PRIMARY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class ServiceHealthCheck(Base):
    """Model for storing service health check results"""
    __tablename__ = "service_health_checks"

    id = Column(Integer, primary_key=True)
    hostname = Column(String(255), nullable=False)
    local_ip = Column(String(50), nullable=False)
    public_ip = Column(String(50), nullable=False)
    service_group = Column(String(50), nullable=False)
    service_name = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    response_time = Column(Float)
    url = Column(Text)
    extra_data = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables if they don't exist"""
    inspector = inspect(engine)
    
    # Create tables if they don't exist
    if not inspector.has_table("service_health_checks"):
        Base.metadata.create_all(engine)

# Initialize the database on startup
init_db() 
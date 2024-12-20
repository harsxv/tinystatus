from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Float,
    Text,
    inspect,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import bcrypt
import secrets

from .config import get_settings

settings = get_settings()

engine = create_engine(settings.PRIMARY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    api_token = Column(String(64), unique=True, nullable=True)
    token_expiry = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)

    def __init__(self, username: str):
        self.username = username

    def set_password(self, password: str):
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode(), salt).decode()

    def check_password(self, password: str) -> bool:
        return bcrypt.checkpw(password.encode(), self.password_hash.encode())

    def generate_token(self, expires_in_days: int = None):
        """Generate new API token with optional expiry"""
        self.api_token = secrets.token_urlsafe(32)
        if expires_in_days:
            self.token_expiry = datetime.utcnow() + timedelta(days=expires_in_days)
        else:
            self.token_expiry = None
        return self.api_token

    def is_token_valid(self) -> bool:
        """Check if token is valid and not expired"""
        if not self.api_token:
            return False
        if self.token_expiry and datetime.utcnow() > self.token_expiry:
            return False
        return True

    def revoke_token(self):
        """Revoke the current API token"""
        self.api_token = None
        self.token_expiry = None


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


class ServiceRecovery(Base):
    """Model for storing service recovery states"""
    __tablename__ = "service_recoveries"

    id = Column(Integer, primary_key=True)
    service_group = Column(String(50), nullable=False)
    service_name = Column(String(50), nullable=False)
    status = Column(String(20), nullable=False)
    stage = Column(String(50))
    error = Column(Text)
    hostname = Column(String(255))
    local_ip = Column(String(50))
    public_ip = Column(String(50))
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime)
    stabilization_end_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
    if not inspector.has_table("users"):
        Base.metadata.create_all(engine)
    if not inspector.has_table("service_recoveries"):
        Base.metadata.create_all(engine)


# Initialize the database on startup
init_db()

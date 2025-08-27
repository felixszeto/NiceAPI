from sqlalchemy import Boolean, Column, Integer, String, Float, DateTime, ForeignKey, Table, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import pytz
from .database import Base
from datetime import datetime

TAIPEI_TZ = pytz.timezone('Asia/Taipei')

# Association Table for the many-to-many relationship between ApiProvider and Group
provider_group_association = Table('provider_group_association', Base.metadata,
    Column('provider_id', Integer, ForeignKey('api_providers.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('groups.id'), primary_key=True),
    Column('priority', Integer, default=1)
)

# Association Table for the many-to-many relationship between ApiKey and Group
api_key_group_association = Table('api_key_group_association', Base.metadata,
    Column('api_key_id', Integer, ForeignKey('api_keys.id'), primary_key=True),
    Column('group_id', Integer, ForeignKey('groups.id'), primary_key=True)
)

class ApiProvider(Base):
    __tablename__ = "api_providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    api_endpoint = Column(String, nullable=False)
    api_key = Column(String, nullable=False)
    model = Column(String, index=True)
    price_per_million_tokens = Column(Float)
    type = Column(String, default="per_token") # per_token or per_call
    is_active = Column(Boolean, default=True)
    total_calls = Column(Integer, default=0)
    successful_calls = Column(Integer, default=0)

    call_logs = relationship("CallLog", back_populates="provider")
    groups = relationship("Group",
                          secondary=provider_group_association,
                          back_populates="providers")

class Group(Base):
    __tablename__ = "groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    
    providers = relationship("ApiProvider",
                             secondary=provider_group_association,
                             back_populates="groups")


    api_keys = relationship("APIKey",
                            secondary=api_key_group_association,
                            back_populates="groups")

class APIKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(TAIPEI_TZ))
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    groups = relationship("Group",
                          secondary=api_key_group_association,
                          back_populates="api_keys")

class CallLog(Base):
    __tablename__ = "call_logs"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(Integer, ForeignKey("api_providers.id"))
    request_timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(TAIPEI_TZ))
    response_timestamp = Column(DateTime(timezone=True), nullable=True)
    is_success = Column(Boolean, nullable=False)
    status_code = Column(Integer)
    response_time_ms = Column(Integer)
    error_message = Column(String, nullable=True)
    response_body = Column(Text, nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    cost = Column(Float, nullable=True)

    provider = relationship("ApiProvider", back_populates="call_logs")

class ErrorMaintenance(Base):
    __tablename__ = "error_maintenance"

    id = Column(Integer, primary_key=True, index=True)
    keyword = Column(String, unique=True, index=True, nullable=False)
    description = Column(String, nullable=True)
    # We can link this to a provider if we want to have provider-specific keywords
    # provider_id = Column(Integer, ForeignKey("api_providers.id"), nullable=True)
    last_triggered = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

class Setting(Base):
    __tablename__ = "settings"

    key = Column(String, primary_key=True, index=True)
    value = Column(String, nullable=False)

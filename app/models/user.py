"""
User Model
Synced with Firebase Authentication
"""

from sqlalchemy import Column, Integer, String, Boolean, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    firebase_uid = Column(String(128), unique=True, nullable=False, index=True)
    phone_number = Column(String(15), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    
    gender = Column(
        Enum("MALE", "FEMALE", "OTHER", name="gender_enum"),
        nullable=False
    )
    profile_image_url = Column(String(255), nullable=True)
    
    is_active = Column(Boolean, default=True)
    total_rides = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    group_memberships = relationship("GroupMember", back_populates="user")
    booking_requests = relationship("BookingRequest", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, name={self.full_name}, phone={self.phone_number})>"
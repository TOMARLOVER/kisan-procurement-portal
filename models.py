from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
import enum
from datetime import datetime
from database import Base

class RoleEnum(str, enum.Enum):
    FARMER = "FARMER"
    ADMIN = "ADMIN"

class StatusEnum(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    aadhaar_number = Column(String(12), unique=True, index=True, nullable=True) # Admin might not need Aadhaar
    username = Column(String(50), unique=True, index=True, nullable=True) # For Admin login
    password_hash = Column(String(255))
    role = Column(Enum(RoleEnum), default=RoleEnum.FARMER)
    full_name = Column(String(100))
    phone = Column(String(15))
    
    profile = relationship("FarmerProfile", back_populates="user", uselist=False)
    transactions = relationship("Transaction", back_populates="farmer")
    slots = relationship("SlotBooking", back_populates="farmer")

class FarmerProfile(Base):
    __tablename__ = "farmer_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    land_area_hectares = Column(Float, default=0.0)
    land_area_acres = Column(Float, default=0.0)
    document_url = Column(String(255), nullable=True)
    total_revenue = Column(Float, default=0.0)
    
    user = relationship("User", back_populates="profile")

class Crop(Base):
    __tablename__ = "crops"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True)
    price_per_quintal = Column(Float)

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    farmer_id = Column(Integer, ForeignKey("users.id"))
    crop_id = Column(Integer, ForeignKey("crops.id"))
    quantity_quintals = Column(Float)
    amount_calculated = Column(Float)
    status = Column(Enum(StatusEnum), default=StatusEnum.PENDING)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    farmer = relationship("User", back_populates="transactions")
    crop = relationship("Crop")
    slot = relationship("SlotBooking", back_populates="transaction", uselist=False)

class SlotBooking(Base):
    __tablename__ = "slot_bookings"
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"))
    farmer_id = Column(Integer, ForeignKey("users.id"))
    scheduled_date = Column(DateTime)
    queue_number = Column(Integer)
    status = Column(Enum(StatusEnum), default=StatusEnum.PENDING)
    
    transaction = relationship("Transaction", back_populates="slot")
    farmer = relationship("User", back_populates="slots")

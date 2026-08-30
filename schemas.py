from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from models import RoleEnum, StatusEnum

# --- Auth ---
class FarmerRegister(BaseModel):
    aadhaar_number: str
    password: str
    full_name: str
    phone: str

class AdminRegister(BaseModel):
    username: str
    password: str
    full_name: str
    phone: str

class LoginRequest(BaseModel):
    identifier: str # can be aadhaar or username
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# --- User & Profile ---
class ProfileUpdate(BaseModel):
    land_area_hectares: Optional[float] = None
    land_area_acres: Optional[float] = None

class FarmerProfileResponse(BaseModel):
    land_area_hectares: Optional[float] = 0.0
    land_area_acres: Optional[float] = 0.0
    document_url: Optional[str]
    total_revenue: float
    class Config:
        from_attributes = True
        orm_mode = True

class UserResponse(BaseModel):
    id: int
    full_name: str
    phone: str
    role: RoleEnum
    aadhaar_number: Optional[str]
    profile: Optional[FarmerProfileResponse]
    class Config:
        from_attributes = True
        orm_mode = True

# --- Crop ---
class CropBase(BaseModel):
    name: str
    price_per_quintal: float

class CropCreate(CropBase):
    pass

class CropResponse(CropBase):
    id: int
    class Config:
        from_attributes = True
        orm_mode = True

class CropPriceUpdate(BaseModel):
    price_per_quintal: float

# --- Transaction & Slot ---
class SlotBookingCreate(BaseModel):
    crop_id: int
    quantity_quintals: float

class SlotResponse(BaseModel):
    id: int
    transaction_id: int
    scheduled_date: datetime
    queue_number: int
    status: StatusEnum
    class Config:
        from_attributes = True
        orm_mode = True

class TransactionResponse(BaseModel):
    id: int
    crop: CropResponse
    quantity_quintals: float
    amount_calculated: float
    status: StatusEnum
    created_at: datetime
    slot: Optional[SlotResponse]
    class Config:
        from_attributes = True
        orm_mode = True

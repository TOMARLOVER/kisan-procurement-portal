from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from fastapi import HTTPException
import models, schemas, auth
from datetime import datetime, timedelta, date

DAILY_CAPACITY = 50

def seed_initial_data(db: Session):
    if db.query(models.Crop).count() == 0:
        default_crops = [
            models.Crop(name="Wheat", price_per_quintal=2275.0),
            models.Crop(name="Rice", price_per_quintal=2183.0),
            models.Crop(name="Maize", price_per_quintal=2090.0),
            models.Crop(name="Cotton", price_per_quintal=6620.0),
            models.Crop(name="Sugarcane", price_per_quintal=315.0),
        ]
        db.add_all(default_crops)
        db.commit()

    admin_user = db.query(models.User).filter(models.User.role == models.RoleEnum.ADMIN).first()
    if not admin_user:
        hashed = auth.get_password_hash("adminpassword")
        default_admin = models.User(
            username="admin",
            password_hash=hashed,
            full_name="System Admin",
            phone="0000000000",
            role=models.RoleEnum.ADMIN
        )
        db.add(default_admin)
        db.commit()

def get_user_by_aadhaar(db: Session, aadhaar_number: str):
    return db.query(models.User).filter(models.User.aadhaar_number == aadhaar_number).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def create_farmer(db: Session, user: schemas.FarmerRegister):
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        aadhaar_number=user.aadhaar_number,
        password_hash=hashed_password,
        full_name=user.full_name,
        phone=user.phone,
        role=models.RoleEnum.FARMER
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Create empty profile
    db_profile = models.FarmerProfile(user_id=db_user.id)
    db.add(db_profile)
    db.commit()
    
    return db_user

def create_admin(db: Session, user: schemas.AdminRegister):
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        password_hash=hashed_password,
        full_name=user.full_name,
        phone=user.phone,
        role=models.RoleEnum.ADMIN
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_farmer_profile(db: Session, user_id: int, profile_update: schemas.ProfileUpdate):
    profile = db.query(models.FarmerProfile).filter(models.FarmerProfile.user_id == user_id).first()
    if not profile:
        profile = models.FarmerProfile(user_id=user_id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        
    if profile_update.land_area_acres is not None:
        profile.land_area_acres = profile_update.land_area_acres
        profile.land_area_hectares = round(profile_update.land_area_acres * 0.404686, 2)
    elif profile_update.land_area_hectares is not None:
        profile.land_area_hectares = profile_update.land_area_hectares
        profile.land_area_acres = round(profile_update.land_area_hectares * 2.47105, 2)
    db.commit()
    db.refresh(profile)
    return profile

# Crops
def get_crops(db: Session):
    return db.query(models.Crop).all()

def get_crop(db: Session, crop_id: int):
    return db.query(models.Crop).filter(models.Crop.id == crop_id).first()

def create_crop(db: Session, crop: schemas.CropCreate):
    db_crop = models.Crop(name=crop.name, price_per_quintal=crop.price_per_quintal)
    db.add(db_crop)
    db.commit()
    db.refresh(db_crop)
    return db_crop

def update_crop_price(db: Session, crop_id: int, price: float):
    crop = db.query(models.Crop).filter(models.Crop.id == crop_id).first()
    if crop:
        crop.price_per_quintal = price
        db.commit()
        db.refresh(crop)
    return crop

# Booking Logic
def find_next_available_slot(db: Session):
    # Start checking from tomorrow
    target_date = date.today() + timedelta(days=1)
    
    while True:
        # Count slots for target_date
        count = db.query(models.SlotBooking).filter(
            func.date(models.SlotBooking.scheduled_date) == target_date
        ).count()
        
        if count < DAILY_CAPACITY:
            return datetime.combine(target_date, datetime.min.time()), count + 1
        
        target_date += timedelta(days=1)

def book_slot(db: Session, user_id: int, booking: schemas.SlotBookingCreate):
    # 1. Rule: Only 1 slot booking per year
    current_year = datetime.now().year
    existing_booking = db.query(models.SlotBooking).filter(
        models.SlotBooking.farmer_id == user_id,
        extract('year', models.SlotBooking.scheduled_date) == current_year
    ).first()
    if existing_booking:
        raise HTTPException(
            status_code=400,
            detail=f"Annual Booking Limit Reached: You have already booked your crop procurement slot for {current_year}. Government rules permit only 1 slot per farmer per year."
        )

    # 2. Rule: Check land area details exist
    profile = db.query(models.FarmerProfile).filter(models.FarmerProfile.user_id == user_id).first()
    if not profile or (profile.land_area_acres or 0.0) <= 0:
        raise HTTPException(
            status_code=400,
            detail="Land Details Required: Please enter your land area details before booking a slot."
        )

    # 3. Rule: Capped maximum crop weight = land_area_acres * 10
    max_allowed = round(profile.land_area_acres * 10.0, 2)
    if booking.quantity_quintals > max_allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum Quantity Exceeded: Based on your registered land area ({profile.land_area_acres} Acres), the maximum weight allowed is {max_allowed} Quintals. You cannot enter more than the maximum limit."
        )

    crop = get_crop(db, booking.crop_id)
    if not crop:
        raise HTTPException(status_code=400, detail="Invalid crop selected.")

    amount = crop.price_per_quintal * booking.quantity_quintals

    # Create Transaction
    db_transaction = models.Transaction(
        farmer_id=user_id,
        crop_id=booking.crop_id,
        quantity_quintals=booking.quantity_quintals,
        amount_calculated=amount,
        status=models.StatusEnum.PENDING
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)

    # Schedule Slot
    scheduled_date, queue_number = find_next_available_slot(db)
    
    db_slot = models.SlotBooking(
        transaction_id=db_transaction.id,
        farmer_id=user_id,
        scheduled_date=scheduled_date,
        queue_number=queue_number,
        status=models.StatusEnum.PENDING
    )
    db.add(db_slot)
    db.commit()
    db.refresh(db_slot)

    return db_transaction

def get_farmer_transactions(db: Session, user_id: int):
    return db.query(models.Transaction).filter(models.Transaction.farmer_id == user_id).order_by(models.Transaction.created_at.desc()).all()

def complete_slot_transaction(db: Session, slot_id: int):
    slot = db.query(models.SlotBooking).filter(models.SlotBooking.id == slot_id).first()
    if not slot or slot.status == models.StatusEnum.COMPLETED:
        return None
    
    slot.status = models.StatusEnum.COMPLETED
    slot.transaction.status = models.StatusEnum.COMPLETED
    
    # Update total revenue for farmer
    profile = db.query(models.FarmerProfile).filter(models.FarmerProfile.user_id == slot.farmer_id).first()
    if profile:
        profile.total_revenue += slot.transaction.amount_calculated
    
    db.commit()
    return slot

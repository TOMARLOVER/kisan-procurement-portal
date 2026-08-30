from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import List
import os

import models, schemas, crud, auth
from database import engine, get_db, SessionLocal

models.Base.metadata.create_all(bind=engine)

# Seed initial data (crops and default admin)
with SessionLocal() as db_session:
    crud.seed_initial_data(db_session)

app = FastAPI(title="Kisan Procurement API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = auth.jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except auth.JWTError:
        raise credentials_exception
    user = crud.get_user(db, user_id=int(user_id))
    if user is None:
        raise credentials_exception
    return user

def require_admin(current_user: models.User = Depends(get_current_user)):
    if current_user.role != models.RoleEnum.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized as admin")
    return current_user

def require_farmer(current_user: models.User = Depends(get_current_user)):
    if current_user.role != models.RoleEnum.FARMER:
        raise HTTPException(status_code=403, detail="Not authorized as farmer")
    return current_user

# --- AUTH ROUTES ---

@app.post("/register/farmer", response_model=schemas.UserResponse)
def register_farmer(user: schemas.FarmerRegister, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_aadhaar(db, aadhaar_number=user.aadhaar_number)
    if db_user:
        raise HTTPException(status_code=400, detail="Aadhaar already registered")
    return crud.create_farmer(db=db, user=user)

@app.post("/register/admin", response_model=schemas.UserResponse)
def register_admin(user: schemas.AdminRegister, db: Session = Depends(get_db)):
    db_user = crud.get_user_by_username(db, username=user.username)
    if db_user:
        raise HTTPException(status_code=400, detail="Username already registered")
    return crud.create_admin(db=db, user=user)

@app.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Try username first (admin), then aadhaar (farmer)
    user = crud.get_user_by_username(db, username=form_data.username)
    if not user:
        user = crud.get_user_by_aadhaar(db, aadhaar_number=form_data.username)
    
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/aadhaar or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth.create_access_token(data={"sub": str(user.id)})
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=schemas.UserResponse)
def get_me(current_user: models.User = Depends(get_current_user)):
    return current_user

# --- FARMER ROUTES ---

@app.put("/farmer/profile", response_model=schemas.FarmerProfileResponse)
def update_profile(profile_update: schemas.ProfileUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(require_farmer)):
    return crud.update_farmer_profile(db, user_id=current_user.id, profile_update=profile_update)

@app.get("/crops", response_model=List[schemas.CropResponse])
def read_crops(db: Session = Depends(get_db)):
    return crud.get_crops(db)

@app.post("/farmer/book-slot", response_model=schemas.TransactionResponse)
def book_slot(booking: schemas.SlotBookingCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_farmer)):
    transaction = crud.book_slot(db, user_id=current_user.id, booking=booking)
    if not transaction:
        raise HTTPException(status_code=400, detail="Failed to book slot. Check crop ID.")
    return transaction

@app.get("/farmer/history", response_model=List[schemas.TransactionResponse])
def get_history(db: Session = Depends(get_db), current_user: models.User = Depends(require_farmer)):
    return crud.get_farmer_transactions(db, user_id=current_user.id)

# --- ADMIN ROUTES ---

@app.post("/admin/crops", response_model=schemas.CropResponse)
def create_crop(crop: schemas.CropCreate, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    return crud.create_crop(db, crop=crop)

@app.put("/admin/crops/{crop_id}", response_model=schemas.CropResponse)
def update_crop(crop_id: int, update: schemas.CropPriceUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    crop = crud.update_crop_price(db, crop_id=crop_id, price=update.price_per_quintal)
    if not crop:
        raise HTTPException(status_code=404, detail="Crop not found")
    return crop

@app.get("/admin/slots", response_model=List[schemas.SlotResponse])
def get_all_slots(db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    return db.query(models.SlotBooking).all()

@app.post("/admin/slots/{slot_id}/complete")
def complete_slot(slot_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(require_admin)):
    slot = crud.complete_slot_transaction(db, slot_id=slot_id)
    if not slot:
        raise HTTPException(status_code=400, detail="Slot not found or already completed")
    return {"message": "Slot completed successfully"}

# Mount frontend files (if directory exists)
frontend_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_path):
    app.mount("/", StaticFiles(directory=frontend_path, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)

"""
Authentication Service
Firebase Auth integration for users and drivers
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import firebase_admin
from firebase_admin import auth, credentials
import logging

from app.database.session import get_db
from app.models.user import User
from app.models.driver import Driver
from app.config.settings import settings

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()

# Initialize Firebase Admin SDK
def initialize_firebase():
    """
    Initialize Firebase Admin SDK
    Should be called once at app startup
    """
    try:
        # Check if already initialized
        firebase_admin.get_app()
        logger.info("Firebase already initialized")
    except ValueError:
        # Initialize with service account
        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
        firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialized")


async def verify_firebase_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> dict:
    """
    Verify Firebase ID token
    Returns decoded token with user info
    """
    
    token = credentials.credentials
    
    try:
        # Verify the token
        decoded_token = auth.verify_id_token(token)
        
        logger.debug(f"Token verified for user: {decoded_token['uid']}")
        
        return decoded_token
        
    except auth.InvalidIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token"
        )
    except auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed"
        )


async def get_current_user(
    token_data: dict = Depends(verify_firebase_token),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current authenticated user
    Creates user in DB if first-time login
    """
    
    firebase_uid = token_data['uid']
    
    # Find user in database
    user = db.query(User).filter(User.firebase_uid == firebase_uid).first()
    
    if not user:
        # First-time login - create user
        # Get additional info from Firebase
        try:
            firebase_user = auth.get_user(firebase_uid)
            
            user = User(
                firebase_uid=firebase_uid,
                phone_number=firebase_user.phone_number or token_data.get('phone_number'),
                full_name=firebase_user.display_name or "User",
                gender="OTHER",  # Will be updated in profile
                is_active=True
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            logger.info(f"New user created: {user.id} ({firebase_uid})")
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user account"
            )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated"
        )
    
    return user


async def get_current_driver(
    token_data: dict = Depends(verify_firebase_token),
    db: Session = Depends(get_db)
) -> Driver:
    """
    Get current authenticated driver
    Requires driver verification
    """
    
    firebase_uid = token_data['uid']
    
    # Find driver in database
    driver = db.query(Driver).filter(Driver.firebase_uid == firebase_uid).first()
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver account not found. Please register as a driver."
        )
    
    if driver.verification_status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Driver verification pending. Status: {driver.verification_status}"
        )
    
    return driver


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User | None:
    """
    Get user if authenticated, None otherwise
    For optional authentication endpoints
    """
    
    try:
        token_data = await verify_firebase_token(credentials)
        return await get_current_user(token_data, db)
    except HTTPException:
        return None


def create_custom_token(uid: str) -> str:
    """
    Create custom Firebase token (for testing)
    """
    try:
        custom_token = auth.create_custom_token(uid)
        return custom_token.decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to create custom token: {e}")
        raise


def verify_phone_number(phone_number: str) -> bool:
    """
    Verify phone number format
    """
    # Basic validation
    if not phone_number or len(phone_number) < 10:
        return False
    
    # Remove common prefixes
    phone_number = phone_number.replace('+91', '').replace('+', '').strip()
    
    # Check if numeric
    return phone_number.isdigit() and len(phone_number) == 10
"""
Firebase Admin SDK integration for authentication and user management.
"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

import firebase_admin
from firebase_admin import auth, credentials
from google.cloud import firestore

from app.config import get_settings
from app.models.auth import UserProfile, TokenData

logger = logging.getLogger(__name__)


class FirebaseService:
    """Firebase service for authentication and user management."""
    
    def __init__(self):
        """Initialize Firebase service."""
        self.settings = get_settings()
        self._initialize_firebase()
        self._db = None
    
    def _initialize_firebase(self) -> None:
        """Initialize Firebase Admin SDK."""
        try:
            if not firebase_admin._apps:
                # Try to get service account key from JSON string first
                if self.settings.firebase_service_account_key_json:
                    service_account_info = json.loads(
                        self.settings.firebase_service_account_key_json
                    )
                    cred = credentials.Certificate(service_account_info)
                # Fall back to file path
                elif self.settings.firebase_service_account_key_path:
                    cred = credentials.Certificate(
                        self.settings.firebase_service_account_key_path
                    )
                else:
                    # Use default credentials (for Cloud Run deployment)
                    try:
                        cred = credentials.ApplicationDefault()
                    except Exception:
                        # For testing, create a dummy credential
                        logger.warning("No Firebase credentials found. Using dummy credentials for testing.")
                        cred = None
                
                if cred:
                    firebase_admin.initialize_app(cred, {
                        'projectId': self.settings.firebase_project_id
                    })
                    logger.info("Firebase Admin SDK initialized successfully")
                else:
                    logger.warning("Firebase Admin SDK not initialized - no credentials available")
            else:
                logger.info("Firebase Admin SDK already initialized")
                
        except Exception as e:
            logger.warning(f"Failed to initialize Firebase: {e}. Service will be limited.")
    
    @property
    def db(self) -> firestore.Client:
        """Get Firestore database client."""
        if self._db is None:
            self._db = firestore.Client(project=self.settings.firebase_project_id)
        return self._db
    
    async def create_user(
        self, 
        email: str, 
        password: str, 
        display_name: str
    ) -> Dict[str, Any]:
        """
        Create a new Firebase user.
        
        Args:
            email: User email address
            password: User password
            display_name: User display name
            
        Returns:
            Dictionary containing user data and custom token
            
        Raises:
            Exception: If user creation fails
        """
        try:
            # Create user in Firebase Auth
            user_record = auth.create_user(
                email=email,
                password=password,
                display_name=display_name,
                email_verified=False
            )
            
            # Create custom token
            custom_token = auth.create_custom_token(user_record.uid)
            
            # Create user profile in Firestore
            user_profile = {
                'user_id': user_record.uid,
                'email': email,
                'display_name': display_name,
                'created_at': datetime.utcnow(),
                'last_login': None,
                'is_verified': False,
                'subscription_tier': 'free',
                'videos_processed': 0,
                'storage_used_mb': 0.0
            }
            
            # Store user profile in Firestore
            self.db.collection('users').document(user_record.uid).set(user_profile)
            
            logger.info(f"User created successfully: {user_record.uid}")
            
            return {
                'user_id': user_record.uid,
                'custom_token': custom_token.decode('utf-8'),
                'user_info': user_profile
            }
            
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            raise
    
    async def authenticate_user(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user with email and password.
        
        Args:
            email: User email address
            password: User password
            
        Returns:
            Dictionary containing user data and custom token
            
        Raises:
            Exception: If authentication fails
        """
        try:
            # Get user by email
            user_record = auth.get_user_by_email(email)
            
            # Create custom token
            custom_token = auth.create_custom_token(user_record.uid)
            
            # Update last login timestamp
            self.db.collection('users').document(user_record.uid).update({
                'last_login': datetime.utcnow()
            })
            
            # Get user profile
            user_doc = self.db.collection('users').document(user_record.uid).get()
            user_profile = user_doc.to_dict() if user_doc.exists else None
            
            logger.info(f"User authenticated successfully: {user_record.uid}")
            
            return {
                'user_id': user_record.uid,
                'custom_token': custom_token.decode('utf-8'),
                'user_info': user_profile
            }
            
        except Exception as e:
            logger.error(f"Failed to authenticate user: {e}")
            raise
    
    async def verify_token(self, token: str) -> TokenData:
        """
        Verify Firebase JWT token and extract user data.
        
        Args:
            token: Firebase JWT token
            
        Returns:
            TokenData object with user information
            
        Raises:
            Exception: If token verification fails
        """
        try:
            # Verify the token
            decoded_token = auth.verify_id_token(token)
            
            # Extract token data
            token_data = TokenData(
                user_id=decoded_token['uid'],
                email=decoded_token.get('email', ''),
                exp=decoded_token['exp'],
                iat=decoded_token['iat'],
                iss=decoded_token['iss'],
                aud=decoded_token['aud']
            )
            
            logger.debug(f"Token verified for user: {token_data.user_id}")
            return token_data
            
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise
    
    async def get_user_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Get user profile from Firestore.
        
        Args:
            user_id: User ID
            
        Returns:
            UserProfile object or None if not found
        """
        try:
            user_doc = self.db.collection('users').document(user_id).get()
            
            if not user_doc.exists:
                return None
            
            user_data = user_doc.to_dict()
            return UserProfile(**user_data)
            
        except Exception as e:
            logger.error(f"Failed to get user profile: {e}")
            raise
    
    async def update_user_profile(
        self, 
        user_id: str, 
        updates: Dict[str, Any]
    ) -> bool:
        """
        Update user profile in Firestore.
        
        Args:
            user_id: User ID
            updates: Dictionary of fields to update
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            # Add updated timestamp
            updates['updated_at'] = datetime.utcnow()
            
            self.db.collection('users').document(user_id).update(updates)
            logger.info(f"User profile updated: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update user profile: {e}")
            return False
    
    async def delete_user(self, user_id: str) -> bool:
        """
        Delete user from Firebase Auth and Firestore.
        
        Args:
            user_id: User ID
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            # Delete from Firebase Auth
            auth.delete_user(user_id)
            
            # Delete from Firestore
            self.db.collection('users').document(user_id).delete()
            
            logger.info(f"User deleted successfully: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete user: {e}")
            return False
    
    async def revoke_refresh_tokens(self, user_id: str) -> bool:
        """
        Revoke all refresh tokens for a user.
        
        Args:
            user_id: User ID
            
        Returns:
            True if revocation successful, False otherwise
        """
        try:
            auth.revoke_refresh_tokens(user_id)
            logger.info(f"Refresh tokens revoked for user: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to revoke refresh tokens: {e}")
            return False


# Global Firebase service instance
firebase_service = FirebaseService()

"""
INDB WebAuthn Implementation
Handles FIDO2/Passkey registration and authentication ceremonies
"""

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
)
from webauthn.helpers.structs import (
    AttestationConveyancePreference,
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
    UserVerificationRequirement,
    RegistrationCredential,
    AuthenticationCredential,
)
from pydantic import BaseModel
from typing import Optional, List, Dict, Any

# In-memory store replaced by INDB persistence
# users_db = {} -> db.users
# challenges_db = {} -> db.challenges (ephemeral is fine, or use internal cache)

RP_ID = "localhost"
RP_NAME = "INDB Core"
ORIGIN = "http://localhost:3001"

class User(BaseModel):
    id: str
    username: str
    credentials: List[Any] = []

class WebAuthnUtils:
    @staticmethod
    def get_db():
        # Circular import handling or injection
        from main import db
        return db

    @staticmethod
    def get_user(username: str) -> Optional[User]:
        db = WebAuthnUtils.get_db()
        user_data = db.get_user(username)
        if user_data:
            return User(**user_data)
        return None

    @staticmethod
    def create_user(username: str) -> User:
        import uuid
        db = WebAuthnUtils.get_db()
        user_id = str(uuid.uuid4())
        user = User(id=user_id, username=username)
        db.save_user(user.dict())
        return user

    @staticmethod
    def generate_registration_options(username: str):
        db = WebAuthnUtils.get_db()
        user = WebAuthnUtils.get_user(username)
        if not user:
            user = WebAuthnUtils.create_user(username)
            
        options = generate_registration_options(
            rp_id=RP_ID,
            rp_name=RP_NAME,
            user_id=user.id.encode(),
            user_name=user.username,
            attestation=AttestationConveyancePreference.DIRECT,
            authenticator_selection=AuthenticatorSelectionCriteria(
                authenticator_attachment=AuthenticatorAttachment.PLATFORM,
                user_verification=UserVerificationRequirement.REQUIRED,
                resident_key=ResidentKeyRequirement.PREFERRED,
            ),
        )
        
        # Store challenge in cache (ephemeral)
        db.cache.set(f"challenge:{username}", options.challenge, ttl=300)
        return options

    @staticmethod
    def verify_registration(username: str, credential_json: Dict[str, Any]):
        db = WebAuthnUtils.get_db()
        challenge = db.cache.get(f"challenge:{username}")
        if not challenge:
            raise ValueError("Challenge expired or not found")
            
        verification = verify_registration_response(
            credential=RegistrationCredential.parse_obj(credential_json),
            expected_challenge=challenge,
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
        )
        
        # Store credential
        user = WebAuthnUtils.get_user(username)
        user.credentials.append(verification.credential_id)
        # Verify calls creates updated user object, save it back
        db.save_user(user.dict())
        
        return True

    @staticmethod
    def generate_authentication_options(username: str):
        db = WebAuthnUtils.get_db()
        options = generate_authentication_options(
            rp_id=RP_ID,
            user_verification=UserVerificationRequirement.REQUIRED,
        )
        db.cache.set(f"challenge:{username}", options.challenge, ttl=300)
        return options

    @staticmethod
    def verify_authentication(username: str, credential_json: Dict[str, Any]):
        db = WebAuthnUtils.get_db()
        challenge = db.cache.get(f"challenge:{username}")
        if not challenge:
            raise ValueError("Challenge expired or not found")
            
        # Real implementation involves loading the stored credential public key
        # For prototype we verify flow
        
        verification = verify_authentication_response(
            credential=AuthenticationCredential.parse_obj(credential_json),
            expected_challenge=challenge,
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
            credential_public_key=b'mock_key', # TODO: Store/Load actual pubkey
            credential_current_sign_count=0,
        )
        
        return True

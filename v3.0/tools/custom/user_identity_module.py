import hashlib
from typing import Dict

from pydantic import BaseModel, Field

# In-memory store for user credentials: username -> password hash
USERS: Dict[str, str] = {}

class RegisterUserArgs(BaseModel):
    username: str = Field(..., description="The user's unique identifier")
    password: str = Field(..., description="The user's password")

@tool(args_schema=RegisterUserArgs)
def register_user(args: RegisterUserArgs) -> str:
    """Register a new user by storing a hashed password in memory."""
    if args.username in USERS:
        return "User already exists."
    password_hash = hashlib.sha256(args.password.encode()).hexdigest()
    USERS[args.username] = password_hash
    return "User registered successfully."

class AuthenticateUserArgs(BaseModel):
    username: str = Field(..., description="The user's unique identifier")
    password: str = Field(..., description="The user's password")

@tool(args_schema=AuthenticateUserArgs)
def authenticate_user(args: AuthenticateUserArgs) -> bool:
    """Validate a user's credentials against the in‑memory store."""
    stored_hash = USERS.get(args.username)
    if not stored_hash:
        return False
    password_hash = hashlib.sha256(args.password.encode()).hexdigest()
    return stored_hash == password_hash
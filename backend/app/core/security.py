import os
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY") # This should be the ANON key

# Initialize Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    """
    Verifies the Supabase JWT token by asking Supabase Auth directly.
    Returns the user payload/dictionary.
    """
    token = credentials.credentials
    
    try:
        # Remote verification: Ask Supabase "Who is this?"
        # This handles signature, expiration, and algorithms automatically.
        response = supabase.auth.get_user(token)
        
        if not response.user:
            raise HTTPException(status_code=401, detail="Invalid session")
            
        # Return user data as a dict to mimic the previous JWT payload structure
        # The 'sub' claim in JWT usually maps to 'id' in the user object
        user_data = {
            "sub": response.user.id,
            "email": response.user.email,
            "user_metadata": response.user.user_metadata
        }
        return user_data
        
    except Exception as e:
        print(f"Auth Error: {e}")
        raise HTTPException(status_code=401, detail="Invalid token or session expired")

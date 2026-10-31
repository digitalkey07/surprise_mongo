import json
from cryptography.fernet import Fernet
from config import TOKEN_ENCRYPTION_KEY


def create_token(tokenData):
    payload = {
        "user_id":tokenData["id"]
        
    }
    payload_byte = json.dumps(payload).encode("utf-8")
    encrypted_token = Fernet(TOKEN_ENCRYPTION_KEY).encrypt(payload_byte)
    return encrypted_token.decode("utf-8")
def validate_token(token):
    try:
        decrypted_token = Fernet(TOKEN_ENCRYPTION_KEY).decrypt(token.encode("utf-8"), ttl=60 * 60 * 24 * 30)
        payload = json.loads(decrypted_token.decode("utf-8"))
    
        if payload is None:
            return None
        return payload
    except Exception as e:
        print(f"Token validation error: {e}")
        return None
        
        
    
    
    
    


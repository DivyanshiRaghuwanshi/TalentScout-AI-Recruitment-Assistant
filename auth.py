import bcrypt
import os

# The file where we'll store the password hash
HASH_FILE = ".password.hash"

def get_password_hash():
    """Retrieves the stored password hash from the file."""
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, "rb") as f:
            return f.read()
    return None

def set_password(password: str):
    """Hashes a new password and saves it to the file."""
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    with open(HASH_FILE, "wb") as f:
        f.write(hashed_password)

def check_password(password: str):
    """Checks if the provided password matches the stored hash."""
    stored_hash = get_password_hash()
    if stored_hash is None:
        # If no password is set, create a default one and inform the user.
        # This is a one-time setup.
        default_password = "password123"
        set_password(default_password)
        print(f"No password file found. A default password '{default_password}' has been set.")
        # Re-check against the new default password
        return check_password(password)
        
    return bcrypt.checkpw(password.encode('utf-8'), stored_hash)

import os
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
DATABASE_NAME = os.getenv("DATABASE_NAME")
TOKEN_ENCRYPTION_KEY = os.getenv("SHA256_KEY")

USER_TYPE=os.getenv("USER_TYPE")
# MONGODB---------------------------
MONGO_URI = os.getenv("MONGODB_URI")
MONGO_DB_NAME=os.getenv("MONGO_DB_NAME")
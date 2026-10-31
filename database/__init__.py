
from email.policy import default
from enum import unique

from pymongo import MongoClient,ASCENDING
from pymongo.errors import PyMongoError
import certifi


from config import MONGO_URI,MONGO_DB_NAME
# ======================================
# MONGODB CONNECTION
# ======================================
client = MongoClient(
    MONGO_URI,
    tls=True,
    tlsCAFile=certifi.where(),
    serverSelectionTimeoutMS=5000,
    connectTimeoutMS=10000
    )
db = client[MONGO_DB_NAME]
# ======================================
# DATABASE CONNECTION FUNCTION
# ======================================
def get_db():
    return db

# ======================================
# COLLECTION REFERENCES
# ======================================

visitor_logs = db["visitor_logs"]
users = db["users"]
uidata = db["uidata"]


# ======================================
# DATABASE CONNECTION CHECK
# ======================================
def check_database():
    try:
        client.admin.command("ping")
        print("MongoDb connection Succssfully")
        return True
    except PyMongoError as e:
        print("MongoDb connection failed")
        print("Error: " , repr(e))
        return False
        
# ======================================
# DATABASE INDEX CREATION
# ======================================
def create_table():
    visitor_logs.create_index(
        [("ip_address", ASCENDING)]
    )

    visitor_logs.create_index(
        [("visited_at", ASCENDING)],
        expireAfterSeconds=86400
    )
    visitor_logs.create_index(
    [("user_id", ASCENDING)]
    )

    # Users indexes
    users.create_index(
        [("username", ASCENDING)],
        unique=True
    )
  
    users.create_index(
        [("is_verify",ASCENDING)]
    )

    # UI data indexes
    uidata.create_index(
        [("festival_name", ASCENDING)]
    )

    uidata.create_index(
        [("is_active", ASCENDING)]
    )

    print("MongoDB indexes created successfully")

# ======================================
# DATABASE INITIALIZATION
# ======================================

def init_database():

    if check_database():
        create_table()
        print("Database initialized successfully")


# ======================================
# DATABASE CLOSE
# ======================================

def close_database():
    client.close()

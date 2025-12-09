# Dosya adı: db_manager.py
import sqlite3
import hashlib
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

DB_FILE = "passwords.db"

def create_connection():
    return sqlite3.connect(DB_FILE)

def create_tables():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute(""" CREATE TABLE IF NOT EXISTS passwords (
        id integer PRIMARY KEY,
        website text NOT NULL,
        username text NOT NULL,
        password text NOT NULL
    ); """)
    cursor.execute(""" CREATE TABLE IF NOT EXISTS secrets (
        id integer PRIMARY KEY,
        salt blob NOT NULL,
        password_hash blob NOT NULL
    ); """)
    conn.commit()
    conn.close()

def derive_key(password, salt):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))

def encrypt_data(key, plaintext):
    f = Fernet(key)
    return f.encrypt(plaintext.encode()).decode()

def decrypt_data(key, ciphertext):
    f = Fernet(key)
    return f.decrypt(ciphertext.encode()).decode()

# --- Fonksiyonlar artık input almıyor, parametre alıyor ---
def check_user_exists():
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM secrets")
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def create_master_user(password):
    salt = os.urandom(16)
    pwd_hash = hashlib.sha256(salt + password.encode()).digest()
    
    conn = create_connection()
    conn.cursor().execute("INSERT INTO secrets(salt, password_hash) VALUES(?, ?)", (salt, pwd_hash))
    conn.commit()
    conn.close()
    return derive_key(password, salt)

def verify_login(password):
    conn = create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT salt, password_hash FROM secrets LIMIT 1")
    record = cursor.fetchone()
    conn.close()
    
    if not record: return None
    
    stored_salt, stored_hash = record
    input_hash = hashlib.sha256(stored_salt + password.encode()).digest()
    
    if input_hash == stored_hash:
        return derive_key(password, stored_salt)
    return None

def add_password_db(key, website, username, password):
    enc_web = encrypt_data(key, website)
    enc_user = encrypt_data(key, username)
    enc_pass = encrypt_data(key, password)
    
    conn = create_connection()
    conn.cursor().execute("INSERT INTO passwords(website, username, password) VALUES(?,?,?)", 
                          (enc_web, enc_user, enc_pass))
    conn.commit()
    conn.close()

def get_passwords_db(key):
    conn = create_connection()
    rows = conn.cursor().execute("SELECT * FROM passwords").fetchall()
    conn.close()
    
    results = []
    for row in rows:
        try:
            dec_web = decrypt_data(key, row[1])
            dec_user = decrypt_data(key, row[2])
            dec_pass = decrypt_data(key, row[3])
            results.append({"id": row[0], "web": dec_web, "user": dec_user, "pass": dec_pass})
        except:
            pass # Çözülemeyenleri atla
    return results

def delete_password_db(id):
    conn = create_connection()
    conn.cursor().execute("DELETE FROM passwords WHERE id=?", (id,))
    conn.commit()
    conn.close()

# db_manager.py dosyasının en altına ekle:

def update_password_entry(id, key, new_username=None, new_password=None):
    """
    Verilen ID'ye sahip kaydın kullanıcı adını veya şifresini günceller.
    Veriler veritabanına kaydedilmeden önce mutlaka şifrelenir.
    """
    conn = create_connection()
    cursor = conn.cursor()
    
    if new_username:
        enc_user = encrypt_data(key, new_username)
        cursor.execute("UPDATE passwords SET username=? WHERE id=?", (enc_user, id))
        
    if new_password:
        enc_pass = encrypt_data(key, new_password)
        cursor.execute("UPDATE passwords SET password=? WHERE id=?", (enc_pass, id))
        
    conn.commit()
    conn.close()
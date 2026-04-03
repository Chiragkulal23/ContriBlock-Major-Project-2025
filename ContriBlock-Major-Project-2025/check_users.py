#!/usr/bin/env python3
import sqlite3
import os

def check_users():
    db_path = os.path.join('backend', 'instance', 'dev.db')
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get all users
        cursor.execute("SELECT id, name, email FROM users")
        users = cursor.fetchall()
        
        print("Available users:")
        for user in users:
            print(f"  ID: {user[0]}, Name: {user[1]}, Email: {user[2]}")
        
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_users()

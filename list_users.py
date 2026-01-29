
try:
    from create_auth_db import get_db_connection
except ImportError:
    raise ImportError("create_auth_db module required")

def list_all_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print(f"{'ID':<5} {'Username':<20} {'Role':<10} {'Created At'}")
    print("-" * 60)
    
    try:
        cursor.execute("SELECT id, username, role, created_at FROM users")
        
        users = cursor.fetchall()
        for user in users:
            # Handle potential None values for created_at if old data exists
            created_at = user[3] if user[3] else "N/A"
            print(f"{user[0]:<5} {user[1]:<20} {user[2]:<10} {created_at}")
            
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    list_all_users()

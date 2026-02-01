
import pandas as pd
import sqlite3
import os

# Import DB utils from existing module
try:
    from create_auth_db import hash_password, get_db_connection, get_placeholder
except ImportError:
    # This shouldn't happen if create_auth_db is there, but strict fallback is risky with DB change
    raise ImportError("create_auth_db module required")

def import_students(excel_file):
    print(f"Reading from {excel_file}...")
    
    if not os.path.exists(excel_file):
        print(f"Error: File '{excel_file}' not found.")
        return

    try:
        df = pd.read_excel(excel_file)
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        return

    # Normalize column names
    df.columns = df.columns.str.strip()
    
    name_col = next((c for c in df.columns if 'name' in c.lower()), None)
    reg_col = next((c for c in df.columns if any(x in c.lower() for x in ['register', 'reg', 'roll', 'id', 'number'])), None)
    email_col = next((c for c in df.columns if any(x in c.lower() for x in ['email', 'mail', 'e-mail'])), None)

    if not name_col or not reg_col:
        print(f"Could not automatically identify Name and Register Number columns.")
        print(f"Columns found: {list(df.columns)}")
        return

    print(f"Mapped columns: Name='{name_col}', Username='{reg_col}', Email='{email_col or 'Not found'}'")
    if not email_col:
        print("Warning: No email column found. Emails will be empty.")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing students to ensure clean state and correct numbering
    print("Clearing existing students...")
    cursor.execute("DELETE FROM users WHERE role='student'")
    
    credentials = []
    added_count = 0

    # Reset index to ensure it starts from 0 for the enumeration
    df = df.reset_index(drop=True)

    ph = get_placeholder()

    for index, row in df.iterrows():
        name = str(row[name_col]).strip()
        username = str(row[reg_col]).strip()
        email = str(row[email_col]).strip() if email_col and pd.notna(row.get(email_col)) else ''
        
        if not username or username.lower() == 'nan' or not name or name.lower() == 'nan':
            continue
        
        # Clean email if it's 'nan'
        if email.lower() == 'nan':
            email = ''

        # Sequential password generation
        # index is 0-based, so we add 1
        password = f"Aids{index+1}@E"
        hashed_pw = hash_password(password)
        
        try:
            cursor.execute(f'''
                INSERT INTO users (username, password, role, name, email) 
                VALUES ({ph}, {ph}, {ph}, {ph}, {ph})
            ''', (username, hashed_pw, 'student', name, email))
            
            credentials.append({
                'Name': name,
                'Username': username,
                'Password': password,
                'Email': email
            })
            added_count += 1
            
        except Exception as e:
            # Catch duplicate key or integrity errors generically for both DBs
            print(f"Error adding user '{username}': {e}")

    conn.commit()
    conn.close()

    print("-" * 40)
    print(f"Import process completed.")
    print(f"Added: {added_count}")

    if credentials:
        # Save credentials to CSV
        output_csv = 'student_credentials.csv'
        creds_df = pd.DataFrame(credentials)
        creds_df.to_csv(output_csv, index=False)
        print(f"Credentials saved to '{output_csv}'.")
    else:
        print("No new credentials to save.")

if __name__ == "__main__":
    import_students('namelist.xlsx')

# """Test script for debugging API issues"""
# from create_auth_db import get_all_submissions_with_content, get_submission_detail
# from evaluator import find_similar_submissions, calculate_similarity, get_code_hash

# # Test getting submissions
# print("Testing get_all_submissions_with_content...")
# subs = get_all_submissions_with_content()
# print(f"Total submissions: {len(subs)}")

# # Check IDs and types
# print("\nAll submission IDs:")
# for s in subs:
#     sid = s.get('id')
#     print(f"  ID: {sid} (type: {type(sid).__name__}), user: {s.get('username')}")

# # Get the current submission details
# if subs:
#     first_id = subs[0]['id']
#     sub = get_submission_detail(first_id)
#     print(f"\nCurrent submission ID: {sub['id']} (type: {type(sub['id']).__name__})")
    
#     # Manual test of the logic
#     print("\nManual similarity check:")
#     target_hash = get_code_hash(sub['file_content'])
#     print(f"Target hash: {target_hash}")
    
#     for s in subs:
#         if not s.get('file_content'):
#             print(f"  {s['id']}: No content")
#             continue
        
#         is_same = (s.get('id') == sub['id'])
#         sub_hash = get_code_hash(s['file_content'])
#         hash_match = (sub_hash == target_hash)
        
#         print(f"  ID {s['id']}: same={is_same}, hash_match={hash_match}, hash={sub_hash[:8]}...")

# print("\nDone!")

import os
import psycopg2

# Use your environment variables or hardcode for testing
DATABASE_URL= None
print(f"ff:{DATABASE_URL}")
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# cur.execute("""
# CREATE TABLE IF NOT EXISTS questions (
#     id SERIAL PRIMARY KEY,
#     title TEXT NOT NULL,
#     description TEXT,
#     difficulty VARCHAR(20),
#     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
# );
# """)

# conn.commit()
# cur.close()
# conn.close()

# print("Table 'questions' created (if it did not exist).")
cur = conn.cursor()

cur.execute("""
ALTER TABLE questions
ADD COLUMN IF NOT EXISTS created_by TEXT;
""")

conn.commit()
cur.close()
conn.close()

print("Column 'created_by' added to 'questions' table (if it did not exist).")

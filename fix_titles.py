import re
from create_auth_db import get_db_connection, get_placeholder

HARDCODED_TITLES = {
    1: "Check Array is Sorted",
    2: "Find Smallest Number Greater Than Key",
    3: "Every Number Appears Twice Except One",
    4: "Return Index of Element (Ignore First Occurrence)"
}

def fix_titles():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        ph = get_placeholder()

        print("--- Fixing Titles ---")

        # 1. Fetch Dynamic Questions
        dynamic_titles = {}
        try:
            cursor.execute("SELECT id, title FROM questions")
            rows = cursor.fetchall()
            for r in rows:
                dynamic_titles[r[0]] = r[1]
            print(f"Loaded {len(dynamic_titles)} dynamic questions.")
        except Exception as e:
            print(f"Error fetching questions: {e}")

        # Combine titles (Dynamic overrides hardcoded if overlap, which is fine)
        all_titles = {**HARDCODED_TITLES, **dynamic_titles}
        
        # 2. Fetch ALL Submissions (Filter in Python to catch '\r', whitespace, etc)
        cursor.execute("SELECT id, filename, problem_title FROM submissions")
        submissions = cursor.fetchall()

        updated_count = 0
        
        for sub in submissions:
            sid, filename, current_title = sub
            
            # Check if title is effectively empty
            if not current_title or not current_title.strip():
                
                problem_id = None
                
                # Match filename pattern
                m = re.search(r'answer_(\d+)[a-zA-Z]*\.', filename)
                if m:
                    problem_id = int(m.group(1))
                elif filename == 'solution.c':
                    problem_id = 4
                
                # Update if we have an ID and a Title
                if problem_id and problem_id in all_titles:
                    raw_title = all_titles[problem_id]
                    
                    # Ensure prefix match if needed
                    # If raw_title is "Find Maximum...", make it "4. Find Maximum..."
                    prefix = f"{problem_id}. "
                    if not raw_title.startswith(prefix):
                        final_title = f"{problem_id}. {raw_title}"
                    else:
                        final_title = raw_title
                    
                    print(f"Updating ID={sid} (File='{filename}') -> '{final_title}'")
                    
                    update_query = f"UPDATE submissions SET problem_title = {ph} WHERE id = {ph}"
                    cursor.execute(update_query, (final_title, sid))
                    updated_count += 1
                else:
                    # Optional: Print skipped for debugging
                    pass

        conn.commit()
        conn.close()
        print(f"Success! Updated {updated_count} submissions.")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_titles()

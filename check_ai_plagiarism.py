"""
AI Plagiarism Check Script
Analyzes all submissions for AI-generated content and shows a report
"""

from create_auth_db import get_all_submissions_with_content, get_db_connection, get_placeholder, IS_POSTGRES
from evaluator import check_ai_generated
import time

def check_all_submissions_for_ai():
    print("=" * 70)
    print("AI PLAGIARISM CHECK REPORT")
    print("=" * 70)
    
    # Get all submissions
    submissions = get_all_submissions_with_content()
    print(f"\nTotal submissions to analyze: {len(submissions)}\n")
    
    if not submissions:
        print("No submissions found.")
        return
    
    results = []
    
    for i, sub in enumerate(submissions, 1):
        print(f"[{i}/{len(submissions)}] Analyzing {sub['username']} - {sub['problem_title'][:30]}...", end=" ")
        
        if not sub.get('file_content'):
            print("❌ No content")
            continue
        
        try:
            ai_result = check_ai_generated(sub['file_content'])
            ai_score = ai_result['ai_score']
            verdict = ai_result['verdict']
            reason = ai_result['reason']
            
            results.append({
                'id': sub['id'],
                'username': sub['username'],
                'name': sub['name'],
                'problem': sub['problem_title'],
                'ai_score': ai_score,
                'verdict': verdict,
                'reason': reason
            })
            
            # Color code based on score
            if ai_score >= 70:
                status = f"🔴 {ai_score}% - {verdict}"
            elif ai_score >= 40:
                status = f"🟡 {ai_score}% - {verdict}"
            else:
                status = f"🟢 {ai_score}% - {verdict}"
            
            print(status)
            
            # Update database with the AI score
            conn = get_db_connection()
            cursor = conn.cursor()
            ph = get_placeholder()
            cursor.execute(f"UPDATE submissions SET ai_score = {ph} WHERE id = {ph}", (ai_score, sub['id']))
            conn.commit()
            conn.close()
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ Error: {e}")
            results.append({
                'id': sub['id'],
                'username': sub['username'],
                'name': sub['name'],
                'problem': sub['problem_title'],
                'ai_score': 0,
                'verdict': 'Error',
                'reason': str(e)
            })
    
    # Summary Report
    print("\n" + "=" * 70)
    print("SUMMARY REPORT")
    print("=" * 70)
    
    likely_ai = [r for r in results if r['ai_score'] >= 70]
    uncertain = [r for r in results if 40 <= r['ai_score'] < 70]
    likely_human = [r for r in results if r['ai_score'] < 40]
    
    print(f"\n🔴 Likely AI-Generated ({len(likely_ai)}):")
    if likely_ai:
        for r in sorted(likely_ai, key=lambda x: x['ai_score'], reverse=True):
            print(f"   {r['ai_score']:3d}% | {r['name']} ({r['username']}) | {r['reason'][:50]}")
    else:
        print("   None")
    
    print(f"\n🟡 Uncertain ({len(uncertain)}):")
    if uncertain:
        for r in sorted(uncertain, key=lambda x: x['ai_score'], reverse=True):
            print(f"   {r['ai_score']:3d}% | {r['name']} ({r['username']}) | {r['reason'][:50]}")
    else:
        print("   None")
    
    print(f"\n🟢 Likely Human-Written ({len(likely_human)}):")
    if likely_human:
        for r in sorted(likely_human, key=lambda x: x['ai_score'], reverse=True):
            print(f"   {r['ai_score']:3d}% | {r['name']} ({r['username']}) | {r['reason'][:50]}")
    else:
        print("   None")
    
    print("\n" + "=" * 70)
    print(f"Total: {len(results)} | 🔴 AI: {len(likely_ai)} | 🟡 Uncertain: {len(uncertain)} | 🟢 Human: {len(likely_human)}")
    print("=" * 70)
    print("\n✅ AI scores have been saved to the database.")

if __name__ == '__main__':
    check_all_submissions_for_ai()

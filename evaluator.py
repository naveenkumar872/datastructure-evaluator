"""
Evaluator module that uses Groq API to evaluate uploaded code against the problem.
Includes AI detection and code similarity checking.
"""

import os
import hashlib
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from groq import Groq

# Initialize Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def normalize_code(code: str) -> str:
    """
    Normalize code for comparison by removing comments, extra whitespace, 
    and standardizing formatting.
    """
    # Remove single-line comments
    code = re.sub(r'//.*', '', code)
    # Remove multi-line comments
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    # Remove all whitespace and newlines
    code = re.sub(r'\s+', '', code)
    # Convert to lowercase
    code = code.lower()
    return code


def get_code_hash(code: str) -> str:
    """Generate a hash of the normalized code for quick comparison."""
    normalized = normalize_code(code)
    return hashlib.md5(normalized.encode()).hexdigest()


def calculate_similarity(code1: str, code2: str) -> float:
    """
    Calculate similarity between two code snippets.
    Returns a percentage (0-100).
    """
    norm1 = normalize_code(code1)
    norm2 = normalize_code(code2)
    
    if not norm1 or not norm2:
        return 0.0
    
    # Use longest common subsequence ratio
    len1, len2 = len(norm1), len(norm2)
    
    # Quick check - if lengths are very different, similarity is low
    if min(len1, len2) / max(len1, len2) < 0.5:
        return (min(len1, len2) / max(len1, len2)) * 100
    
    # Calculate character-level similarity using set intersection
    set1 = set(norm1[i:i+5] for i in range(len(norm1)-4)) if len(norm1) >= 5 else {norm1}
    set2 = set(norm2[i:i+5] for i in range(len(norm2)-4)) if len(norm2) >= 5 else {norm2}
    
    if not set1 or not set2:
        return 0.0
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    return (intersection / union) * 100 if union > 0 else 0.0


def check_ai_generated(code_content: str) -> dict:
    """
    Use Groq to detect if code appears to be AI-generated.
    Returns AI probability score and indicators.
    """
    prompt = f"""Analyze this code and determine if it appears to be AI-generated (by ChatGPT, Copilot, etc.) or human-written.

CODE:
```c
{code_content}
```

Respond in this EXACT format only:
AI_SCORE: [0-100]
VERDICT: [AI-Generated / Human-Written / Uncertain]
REASON: [One short sentence explaining why]

AI indicators to check:
- Overly consistent formatting and naming conventions
- Generic variable names (i, j, temp, arr, n)
- Perfect comment structure
- Textbook-style implementation
- Lack of personal coding style/quirks

Human indicators:
- Inconsistent formatting/indentation
- Unique variable naming patterns
- Unusual but working approaches
- Minor inefficiencies that work
- Personal coding habits"""

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are an AI detection expert. Be concise."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2,
            max_tokens=200
        )
        
        result_text = response.choices[0].message.content
        
        # Parse the response
        ai_score = 50  # default
        verdict = "Uncertain"
        reason = ""
        
        for line in result_text.split('\n'):
            if 'AI_SCORE:' in line:
                try:
                    ai_score = int(re.search(r'\d+', line).group())
                except:
                    pass
            elif 'VERDICT:' in line:
                verdict = line.split(':', 1)[1].strip()
            elif 'REASON:' in line:
                reason = line.split(':', 1)[1].strip()
        
        return {
            'ai_score': min(100, max(0, ai_score)),
            'verdict': verdict,
            'reason': reason
        }
        
    except Exception as e:
        return {
            'ai_score': 0,
            'verdict': 'Error',
            'reason': str(e)
        }


def extract_text_from_file(file_path: str) -> str:
    """
    Extract text content from a file.
    
    Args:
        file_path: Path to the uploaded file
        
    Returns:
        The text content of the file
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except UnicodeDecodeError:
        # Try with different encoding if utf-8 fails
        with open(file_path, 'r', encoding='latin-1') as f:
            return f.read()


def evaluate_code(problem_statement: str, code_content: str) -> dict:
    """
    Use Groq API to evaluate the submitted code.
    Returns concise 2-3 line feedback for each category.
    """
    
    prompt = f"""Evaluate this code submission. Be VERY CONCISE - max 2 sentences per category.

PROBLEM: {problem_statement}

CODE:
```c
{code_content}
```

Respond in this EXACT format:

Correctness: [0-100]
[2 sentences max about correctness]

Code Quality: [0-100]  
[2 sentences max about quality]

Efficiency: [0-100]
[2 sentences max about efficiency]

Overall Score: [0-100]
[1 sentence summary]"""

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a code evaluator. Be concise - max 2 sentences per section."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.3,
            max_tokens=500
        )
        
        evaluation_text = chat_completion.choices[0].message.content
        
        return {
            "success": True,
            "evaluation": evaluation_text,
            "model": "llama-3.3-70b-versatile"
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "evaluation": None
        }


def evaluate_uploaded_content(code_content: str, problem_statement: str) -> dict:
    """
    Main function to evaluate uploaded code content.
    Includes code evaluation and AI detection.
    """
    
    # Evaluate the code
    result = evaluate_code(problem_statement, code_content)
    
    # Check for AI-generated content
    ai_check = check_ai_generated(code_content)
    result['ai_score'] = ai_check['ai_score']
    result['ai_verdict'] = ai_check['verdict']
    result['ai_reason'] = ai_check['reason']
    
    # Generate code hash for similarity checking
    result['code_hash'] = get_code_hash(code_content)
    
    result["code_preview"] = code_content[:500] + "..." if len(code_content) > 500 else code_content
    
    return result


def find_similar_submissions(code_content: str, all_submissions: list, current_submission_id: int = None, threshold: float = 70.0) -> list:
    """
    Find submissions with similar code.
    
    Args:
        code_content: The code to compare
        all_submissions: List of all submissions with 'file_content' and 'username' keys
        current_submission_id: ID of current submission to exclude from results
        threshold: Minimum similarity percentage to be considered similar
        
    Returns:
        List of similar submissions with similarity scores
    """
    similar = []
    target_hash = get_code_hash(code_content)
    
    for sub in all_submissions:
        if not sub.get('file_content'):
            continue
        
        # Skip current submission
        if current_submission_id and sub.get('id') == current_submission_id:
            continue
            
        sub_hash = get_code_hash(sub['file_content'])
        
        # Quick check - if hashes match, it's 100% similar
        if sub_hash == target_hash:
            similar.append({
                'username': sub.get('username'),
                'name': sub.get('name', sub.get('username')),
                'submission_id': sub.get('id'),
                'similarity': 100.0,
                'problem_title': sub.get('problem_title')
            })
        else:
            # Calculate detailed similarity
            sim = calculate_similarity(code_content, sub['file_content'])
            if sim >= threshold:
                similar.append({
                    'username': sub.get('username'),
                    'name': sub.get('name', sub.get('username')),
                    'submission_id': sub.get('id'),
                    'similarity': round(sim, 1),
                    'problem_title': sub.get('problem_title')
                })
    
    # Sort by similarity (highest first)
    similar.sort(key=lambda x: x['similarity'], reverse=True)
    
    return similar

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


def analyze_code_patterns(code_content: str) -> dict:
    """
    Analyze code patterns to detect AI-generated vs human-written characteristics.
    Returns detailed analysis with scores for each pattern.
    """
    patterns = {
        'ai_indicators': [],
        'human_indicators': [],
        'scores': {}
    }
    
    lines = code_content.split('\n')
    non_empty_lines = [l for l in lines if l.strip()]
    
    # 1. Variable Naming Analysis
    # AI tends to use: arr, n, temp, i, j, result, count, sum, size, len
    ai_var_names = ['arr', 'temp', 'result', 'count', 'sum', 'size', 'len', 'num', 'ptr', 'node']
    human_var_names = ['my', 'the', 'this', 'flag', 'check', 'found', 'ans', 'ret', 'val', 'cnt', 'idx']
    
    var_pattern = re.findall(r'\b(?:int|float|char|double|long)\s+(\w+)', code_content)
    var_pattern += re.findall(r'(\w+)\s*=', code_content)
    
    ai_var_count = sum(1 for v in var_pattern if any(ai in v.lower() for ai in ai_var_names))
    human_var_count = sum(1 for v in var_pattern if any(hv in v.lower() for hv in human_var_names))
    unique_vars = len(set(var_pattern))
    
    if ai_var_count > human_var_count and ai_var_count > 2:
        patterns['ai_indicators'].append(f"Standard variable names ({ai_var_count} AI-typical names)")
        patterns['scores']['variables'] = 70
    elif human_var_count > 0:
        patterns['human_indicators'].append(f"Creative variable naming ({human_var_count} unique names)")
        patterns['scores']['variables'] = 30
    else:
        patterns['scores']['variables'] = 50
    
    # 2. Comment Analysis
    comments = re.findall(r'//.*|/\*[\s\S]*?\*/', code_content)
    comment_count = len(comments)
    
    # AI comments tend to be descriptive and start with capital letters
    descriptive_comments = sum(1 for c in comments if len(c) > 20 and c.strip('/ ')[0:1].isupper())
    short_comments = sum(1 for c in comments if len(c) < 15)
    
    if comment_count > 3 and descriptive_comments > comment_count * 0.6:
        patterns['ai_indicators'].append(f"Well-structured comments ({comment_count} comments, {descriptive_comments} descriptive)")
        patterns['scores']['comments'] = 75
    elif comment_count == 0:
        patterns['human_indicators'].append("No comments (typical human code)")
        patterns['scores']['comments'] = 20
    elif short_comments > comment_count * 0.5:
        patterns['human_indicators'].append(f"Short/terse comments ({short_comments} brief comments)")
        patterns['scores']['comments'] = 25
    else:
        patterns['scores']['comments'] = 50
    
    # 3. Indentation Consistency
    indents = []
    for line in lines:
        if line.strip():
            leading_spaces = len(line) - len(line.lstrip())
            indents.append(leading_spaces)
    
    # Check if indentation follows a consistent pattern (multiples of same number)
    if indents:
        indent_set = set(i for i in indents if i > 0)
        if indent_set:
            # AI typically uses consistent 2 or 4 space indentation
            min_indent = min(indent_set) if indent_set else 4
            consistent = all(i % min_indent == 0 or i == 0 for i in indents)
            
            if consistent and min_indent in [2, 4]:
                patterns['ai_indicators'].append(f"Perfect {min_indent}-space indentation")
                patterns['scores']['indentation'] = 70
            elif not consistent:
                patterns['human_indicators'].append("Inconsistent indentation")
                patterns['scores']['indentation'] = 20
            else:
                patterns['scores']['indentation'] = 50
        else:
            patterns['scores']['indentation'] = 50
    else:
        patterns['scores']['indentation'] = 50
    
    # 4. Code Structure Analysis - Function definitions
    func_defs = re.findall(r'(?:int|void|float|char|double)\s+(\w+)\s*\([^)]*\)\s*\{', code_content)
    
    # AI tends to use descriptive function names
    descriptive_funcs = sum(1 for f in func_defs if len(f) > 8 and ('_' in f or any(c.isupper() for c in f[1:])))
    
    if descriptive_funcs > 0:
        patterns['ai_indicators'].append(f"Descriptive function names ({descriptive_funcs})")
        patterns['scores']['functions'] = 65
    else:
        patterns['scores']['functions'] = 40
    
    # 5. Error Handling / Edge Cases
    error_patterns = ['if.*NULL', 'if.*<.*0', 'if.*==.*0', 'if.*<=.*0', 'return.*-1', 'return.*NULL']
    error_handling = sum(1 for p in error_patterns if re.search(p, code_content))
    
    if error_handling >= 3:
        patterns['ai_indicators'].append(f"Comprehensive error handling ({error_handling} checks)")
        patterns['scores']['error_handling'] = 75
    elif error_handling == 0:
        patterns['human_indicators'].append("No explicit error handling")
        patterns['scores']['error_handling'] = 20
    else:
        patterns['scores']['error_handling'] = 45
    
    # 6. Code Cleanliness - No debugging leftovers
    debug_patterns = ['printf.*debug', 'printf.*test', 'TODO', 'FIXME', 'XXX', '//.*test', 'cout.*<<']
    debug_found = sum(1 for p in debug_patterns if re.search(p, code_content, re.IGNORECASE))
    
    if debug_found > 0:
        patterns['human_indicators'].append(f"Debug/test code found ({debug_found})")
        patterns['scores']['debug'] = 15
    else:
        patterns['scores']['debug'] = 60
    
    # 7. Line Length Analysis
    long_lines = sum(1 for l in lines if len(l) > 80)
    very_long_lines = sum(1 for l in lines if len(l) > 100)
    
    if very_long_lines == 0 and long_lines < len(lines) * 0.1:
        patterns['ai_indicators'].append("Consistent line lengths (< 80 chars)")
        patterns['scores']['line_length'] = 65
    elif very_long_lines > 2:
        patterns['human_indicators'].append("Long lines (human typing)")
        patterns['scores']['line_length'] = 25
    else:
        patterns['scores']['line_length'] = 50
    
    # 8. Blank Line Usage
    blank_sections = re.findall(r'\n\s*\n\s*\n', code_content)
    proper_spacing = len(blank_sections) > 0 and len(blank_sections) < 5
    
    if proper_spacing:
        patterns['scores']['spacing'] = 60
    else:
        patterns['scores']['spacing'] = 45
    
    return patterns


def get_llm_ai_analysis(code_content: str) -> dict:
    """
    Use LLM to provide additional AI detection insights.
    Returns LLM-based AI score and reasoning.
    """
    # Truncate code if too long to save tokens
    code_preview = code_content[:2000] if len(code_content) > 2000 else code_content
    
    prompt = f"""Analyze this C code snippet and determine if it appears AI-generated or human-written.

CODE:
```c
{code_preview}
```

Focus on:
1. Coding style and personal quirks
2. Variable naming creativity
3. Comment naturalness
4. Algorithm approach uniqueness

Respond ONLY in this format:
AI_SCORE: [0-100]
REASON: [One sentence with specific observation from the code]"""

    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a code pattern analyst. Be objective and concise."},
                {"role": "user", "content": prompt}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.1,
            max_tokens=150
        )
        
        result_text = response.choices[0].message.content
        
        ai_score = 50
        reason = ""
        
        for line in result_text.split('\n'):
            line_upper = line.upper()
            if 'AI_SCORE:' in line_upper:
                try:
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        ai_score = int(numbers[0])
                except:
                    pass
            elif 'REASON:' in line_upper:
                reason = line.split(':', 1)[1].strip() if ':' in line else ""
        
        return {
            'ai_score': min(100, max(0, ai_score)),
            'reason': reason if reason else "LLM analysis completed"
        }
        
    except Exception as e:
        # If LLM fails, return neutral score
        return {
            'ai_score': 50,
            'reason': f"LLM unavailable: {str(e)[:50]}"
        }


def check_ai_generated(code_content: str) -> dict:
    """
    HYBRID AI Detection: Combines rule-based pattern analysis with LLM insights.
    - Rule-based analysis: 60% weight (consistent, measurable)
    - LLM analysis: 40% weight (contextual understanding)
    
    Returns AI probability score and indicators.
    """
    # Step 1: Rule-based pattern analysis
    analysis = analyze_code_patterns(code_content)
    
    # Calculate rule-based score
    weights = {
        'variables': 0.20,
        'comments': 0.20,
        'indentation': 0.15,
        'functions': 0.10,
        'error_handling': 0.15,
        'debug': 0.10,
        'line_length': 0.05,
        'spacing': 0.05
    }
    
    rule_score = 0
    for key, weight in weights.items():
        score = analysis['scores'].get(key, 50)
        rule_score += score * weight
    
    # Step 2: LLM-based analysis
    llm_result = get_llm_ai_analysis(code_content)
    llm_score = llm_result['ai_score']
    llm_reason = llm_result['reason']
    
    # Step 3: Combine scores (60% rule-based, 40% LLM)
    # This ensures consistency from rules while getting LLM insights
    combined_score = int(round(rule_score * 0.6 + llm_score * 0.4))
    
    # Build comprehensive reason from both analyses
    indicators = []
    
    # Add rule-based indicators
    if analysis['ai_indicators']:
        indicators.append(f"[Pattern] {analysis['ai_indicators'][0]}")
    if analysis['human_indicators']:
        indicators.append(f"[Pattern] {analysis['human_indicators'][0]}")
    
    # Add LLM insight
    if llm_reason and 'unavailable' not in llm_reason.lower():
        indicators.append(f"[LLM] {llm_reason[:100]}")
    
    # Determine verdict based on combined score
    if combined_score >= 65:
        verdict = "Likely AI"
    elif combined_score <= 35:
        verdict = "Likely Human"
    else:
        verdict = "Uncertain"
    
    reason = "; ".join(indicators) if indicators else "Standard code patterns"
    
    return {
        'ai_score': min(100, max(0, combined_score)),
        'verdict': verdict,
        'reason': reason,
        'rule_score': int(round(rule_score)),
        'llm_score': llm_score,
        'details': analysis
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

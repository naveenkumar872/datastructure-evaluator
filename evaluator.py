"""
Evaluator module that uses Groq API to evaluate uploaded code against the problem.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from groq import Groq

# Initialize Groq client
# Make sure to set GROQ_API_KEY in your .env file
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))



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
    Use Groq API LLM to evaluate the submitted code against the problem statement.
    
    Args:
        problem_statement: The problem description/requirements
        code_content: The extracted code from the uploaded file
        
    Returns:
        Dictionary containing evaluation results
    """
    
    prompt = f"""You are an expert code evaluator and programming instructor. Your task is to evaluate the following code submission against the given problem statement.

## Problem Statement:
{problem_statement}

## Submitted Code:
```c
{code_content}
```

Please provide a detailed evaluation following STRICTLY this format:

Correctness: [Score 0-100]

[Explanation of correctness...]

Code Quality: [Score 0-100]

[Explanation of code quality...]

Efficiency: [Score 0-100]

[Explanation of efficiency...]

Overall Score: [Score 0-100]

[Overall assessment...]

IMPORTANT:
- Do NOT add any other headers like "Strengths", "Weaknesses", "Verdict", or "Introduction" or "Recommandation for improvement" or "Conclusion".    
- Adhere strictly to the "Header: Score" followed by "Text explanation" structure.
"""

    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert code evaluator providing detailed, constructive feedback on code submissions."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            model="llama-3.3-70b-versatile",  # Using Llama 3.3 70B model
            temperature=0.3,  # Lower temperature for more consistent evaluations
            max_tokens=2000
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
    
    Args:
        code_content: The actual code string
        problem_statement: The problem the code should solve
        
    Returns:
        Dictionary containing evaluation results
    """
    
    # Evaluate the code
    result = evaluate_code(problem_statement, code_content)
    result["code_preview"] = code_content[:500] + "..." if len(code_content) > 500 else code_content
    
    return result

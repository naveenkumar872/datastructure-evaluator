# Data Structure Evaluator (demo)

Quick demo of a client-side Data Structure Evaluator. Open `index.html` in a browser to run.

How it works:
- Create a problem using the "Create Problem" button. Fill the title, description and tests JSON.
- Tests are a JSON array, each item must contain `input` and `output` (they can be numbers, strings, arrays or objects).
- When solving, submit JavaScript code that defines a function `solve(input)`.
- The page will run `solve` for each test and compare results by JSON equality.

Limitations:
- This is a browser-only demo. Running arbitrary code via `eval` is unsafe for production.
- No sandboxing or server-side execution; timeouts are basic and may not prevent infinite loops.

To run:

```powershell
# Open the file in your default browser (Windows)
start index.html
```

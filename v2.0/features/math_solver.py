import sympy as sp
from langchain_core.tools import tool

@tool
def solve_equation(equation: str) -> str:
    """
    Evaluates mathematical expressions and equations safely.
    Use this when Mr. Harjas asks you to do math.
    Provide the equation as a string, e.g., 'sqrt(85934) * 12'.
    """
    try:
        # Sympy safely evaluates mathematical strings
        result = sp.sympify(equation).evalf()
        return f"The mathematical result is: {result}"
    except Exception as e:
        return f"MATH ERROR: Could not evaluate equation. Error: {str(e)}"
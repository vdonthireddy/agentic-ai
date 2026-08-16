"""Unit tests for math and python execution tools in mcp-server."""

import pytest
import sys
from pathlib import Path

# Add mcp-server to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.math_tools import calculate, execute_python_code

def test_calculate_basic_arithmetic():
    res = calculate("25 * 4")
    assert res["success"] is True
    assert res["result"] == 100

def test_calculate_complex_expression():
    res = calculate("(100 - 25) / 5 + 2**3")
    assert res["success"] is True
    assert res["result"] == 23.0

def test_calculate_invalid_expression():
    res = calculate("import os; os.system('echo hi')")
    assert res["success"] is False
    assert "error" in res

def test_execute_python_basic():
    code = "x = 10\ny = 20\nz = x + y\nprint('Total is', z)"
    res = execute_python_code(code)
    assert res["success"] is True
    assert "Total is 30" in res["stdout"]
    assert res["variables"]["z"] == "30"

def test_execute_python_prime_function():
    code = """
def is_prime(n):
    if n <= 1:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

primes = [p for p in range(1, 15) if is_prime(p)]
print('Primes:', primes)
"""
    res = execute_python_code(code)
    assert res["success"] is True
    assert "Primes: [2, 3, 5, 7, 11, 13]" in res["stdout"]

def test_execute_python_syntax_repair():
    # Test f-string with unescaped newline
    code = "name = 'Test'\nprint(f'Hello {name}\nWelcome!')"
    res = execute_python_code(code)
    assert res["success"] is True
    assert "Hello Test" in res["stdout"]

def test_calculate_named_parameters():
    # Test formula alias
    res_formula = calculate(formula="15 * 8")
    assert res_formula["success"] is True
    assert res_formula["result"] == 120

    # Test math_expr alias
    res_math = calculate(math_expr="200 / 4")
    assert res_math["success"] is True
    assert res_math["result"] == 50.0

def test_calculate_tip_and_total_combination():
    # Test tip + total parameter combination
    res = calculate(total="184.50", tip="184.50 * 0.18")
    assert res["success"] is True
    assert abs(res["result"] - 217.71) < 0.001

def test_calculate_unary_negation():
    # Test unary operators (-5 + 10)
    res = calculate("-5 + 10")
    assert res["success"] is True
    assert res["result"] == 5

def test_calculate_missing_expression():
    res = calculate()
    assert res["success"] is False
    assert "No mathematical expression" in res["error"]

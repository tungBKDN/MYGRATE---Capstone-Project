import pytest
from src.ast_parser.transformer import modernize_code

def test_modernize_union_basic():
    """Test standard Union[int, str] -> int | str."""
    source = "var: Union[int, str] = 10"
    expected = "var: int | str = 10"
    assert modernize_code(source) == expected

def test_modernize_union_multiple():
    """Test Union with more than 2 types: Union[int, float, str]."""
    source = "def func(a: Union[int, float, str]): pass"
    modernized = modernize_code(source)
    assert "a: int | float | str" in modernized
    assert "pass" in modernized

def test_modernize_optional():
    """Test Optional[bool] -> bool | None."""
    source = "x: Optional[bool] = None"
    expected = "x: bool | None = None"
    assert modernize_code(source) == expected

def test_modernize_nested():
    """Test nested combinations: List[Union[int, str]] -> List[int | str]."""
    source = "data: List[Union[int, str]] = []"
    expected = "data: List[int | str] = []"
    assert modernize_code(source) == expected

def test_modernize_typing_prefix():
    """Test usage of typing.Union and typing.Optional."""
    source = "x: typing.Union[int, str]; y: typing.Optional[float]"
    # Note: ast.unparse might normalize formatting
    modernized = modernize_code(source)
    assert "int | str" in modernized
    assert "float | None" in modernized

def test_logic_preservation():
    """Ensure that non-type hint logic remains unchanged."""
    source = """
def calculate(a: int, b: int) -> int:
    result = a + b
    return result * 2

class MyClass:
    def __init__(self, value: Optional[int]):
        self.value = value
"""
    modernized = modernize_code(source)
    assert "result = a + b" in modernized
    assert "return result * 2" in modernized
    assert "self.value = value" in modernized
    assert "value: int | None" in modernized

def test_deeply_nested():
    """Test deeply nested Union/Optional."""
    source = "x: Union[int, Optional[Union[str, float]]]"
    modernized = modernize_code(source)
    # Removing whitespace and parentheses for a looser check
    flat_modernized = modernized.replace(" ", "").replace("(", "").replace(")", "")
    assert "x:int|str|float|None" in flat_modernized

def test_no_change_needed():
    """Test code that doesn't need modernization."""
    source = "x: int = 5\ny: str = 'hello'"
    assert modernize_code(source) == source

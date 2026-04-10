import pytest
from src.agents.reader import UniversalASTReader

@pytest.fixture
def reader():
    return UniversalASTReader()

def test_parse_python(reader):
    source = b"def foo(): pass"
    tree = reader.parse(source, "python")
    
    assert tree is not None
    assert tree.root_node.type == "module"

def test_parse_java(reader):
    source = b"class MyClass { void foo() {} }"
    tree = reader.parse(source, "java")
    
    assert tree is not None
    assert tree.root_node.type == "program"

def test_query_python_functions(reader):
    source = b"""
def my_func1():
    pass

def my_func2():
    pass
"""
    tree = reader.parse(source, "python")
    query_string = "(function_definition name: (identifier) @func_name)"
    results = reader.query(tree, "python", query_string)
    
    # Verify count and names
    assert len(results) == 2
    
    node1, capture1 = results[0]
    assert capture1 == "func_name"
    assert node1.type == "identifier"
    assert source[node1.start_byte:node1.end_byte].decode("utf-8") == "my_func1"
    
    node2, capture2 = results[1]
    assert capture2 == "func_name"
    assert source[node2.start_byte:node2.end_byte].decode("utf-8") == "my_func2"
    
    # Verify positions (line, column)
    assert node1.start_point == (1, 4)  # 2nd line, 5th col -> 0-indexed is 1, 4
    assert node2.start_point == (4, 4)  # 5th line, 5th col

def test_query_python_union_optional_type_hints(reader):
    source = b"""
from typing import Union, Optional

def process_data(data: Union[int, str], flag: Optional[bool]):
    pass
"""
    tree = reader.parse(source, "python")
    # Query TypeHint using Union or Optional as an example
    query_string = """
    (generic_type 
        (identifier) @type_modifier 
        (#match? @type_modifier "^(Union|Optional)$")
    ) @generic_type
    """
    
    results = reader.query(tree, "python", query_string)
    
    # 4 match tuples in total: Union modifier, Union generic_type, Optional modifier, Optional generic_type
    assert len(results) > 0
    
    # Get only the type modifiers
    modifiers = [
        source[node.start_byte:node.end_byte].decode("utf-8") 
        for node, capture in results if capture == "type_modifier"
    ]
    
    assert "Union" in modifiers
    assert "Optional" in modifiers
    assert modifiers.count("Union") == 1
    assert modifiers.count("Optional") == 1

def test_query_java_methods(reader):
    source = b"""
public class MainApp {
    public void executeLogic() {}
    private int calcSum(int a, int b) { return a + b; }
}
"""
    tree = reader.parse(source, "java")
    query_string = "(method_declaration name: (identifier) @method_id)"
    results = reader.query(tree, "java", query_string)
    
    assert len(results) == 2
    
    node1, capture1 = results[0]
    assert capture1 == "method_id"
    assert node1.type == "identifier"
    assert source[node1.start_byte:node1.end_byte].decode("utf-8") == "executeLogic"
    
    node2, capture2 = results[1]
    assert capture2 == "method_id"
    assert source[node2.start_byte:node2.end_byte].decode("utf-8") == "calcSum"

def test_visualize(reader):
    source = b"def do_work(): pass"
    tree = reader.parse(source, "python")
    output = reader.visualize(tree.root_node, source)
    
    # Verify that the output string isn't empty and contains the appropriate structures
    assert isinstance(output, str)
    assert len(output) > 0
    assert "module" in output
    assert "function_definition" in output
    assert "identifier 'do_work'" in output
    assert "├──" in output
    assert "pass 'pass'" in output

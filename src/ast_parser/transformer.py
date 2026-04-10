import ast
from typing import Optional as TypingOptional, Union as TypingUnion

class TypeHintModernizer(ast.NodeTransformer):
    """
    AST Transformer to modernize Python type hints from Union[X, Y] to X | Y
    and Optional[X] to X | None, adhering to PEP 604 (Python 3.10+).
    """

    def visit_Subscript(self, node: ast.Subscript) -> ast.AST:
        """
        Identify Union and Optional subscripts and transform them into BinOp with BitOr.
        """
        # Visit children first to handle nested definitions like Union[int, Optional[str]]
        self.generic_visit(node)

        name = self._get_name(node.value)
        if name not in ("Union", "Optional"):
            return node

        # Extract elements from the slice
        # In Python 3.9+, node.slice is the node itself (ast.Tuple or regular node)
        # In Python 3.8, node.slice was an ast.Index or ast.ExtSlice
        slice_node = node.slice
        
        # Handle cases where slice might be wrapped (older Python versions compatibility or complex cases)
        if hasattr(ast, 'Index') and isinstance(slice_node, ast.Index):
            slice_node = slice_node.value

        elts = []
        if isinstance(slice_node, ast.Tuple):
            elts = slice_node.elts
        else:
            elts = [slice_node]

        if name == "Optional":
            # Optional[X] becomes X | None
            # Ensure we don't have empty Optional
            if not elts:
                return node
            elts.append(ast.Constant(value=None))

        if not elts:
            return node

        # Construct BinOp chain: elt1 | elt2 | ...
        new_node = elts[0]
        for next_elt in elts[1:]:
            new_node = ast.BinOp(
                left=new_node,
                op=ast.BitOr(),
                right=next_elt
            )
        
        # Copy attributes like lineno, col_offset for the new node
        return ast.copy_location(new_node, node)

    def _get_name(self, node: ast.AST) -> TypingOptional[str]:
        """
        Helper to extract the name of the type being subscripted.
        Handles both 'Union' and 'typing.Union'.
        """
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

def modernize_code(source_code: str) -> str:
    """
    Parses source code, applies the TypeHintModernizer, and returns the modified source.
    
    Args:
        source_code: The Python source code to modernize.
        
    Returns:
        The modernized Python source code.
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        # For a robust tool, we might want to handle this differently,
        # but for PoC we let it raise.
        raise e
        
    transformer = TypeHintModernizer()
    modernized_tree = transformer.visit(tree)
    ast.fix_missing_locations(modernized_tree)
    
    return ast.unparse(modernized_tree)

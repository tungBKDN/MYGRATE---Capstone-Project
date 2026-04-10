import tree_sitter
import tree_sitter_python
import tree_sitter_java


class UniversalASTReader:
    """
    Module AST Parser Agent
    Universal AST Reader that parses and queries Python and Java source code using tree-sitter.
    Preserves 100% of syntax details for syntax modernization without affecting business logic.
    """

    def __init__(self):
        # Load language module according to new tree-sitter API
        self.languages = {
            "python": tree_sitter.Language(tree_sitter_python.language()),
            "java": tree_sitter.Language(tree_sitter_java.language()),
        }

    def parse(self, source_code: bytes, lang: str) -> tree_sitter.Tree:
        """
        Parses the source code and returns the corresponding AST Tree.
        
        Args:
            source_code: Source code in bytes.
            lang: Language ('python', 'java', ...).
            
        Returns:
            tree_sitter.Tree: Root of the syntax tree.
        """
        if lang not in self.languages:
            raise ValueError(f"Language '{lang}' is not supported yet.")

        # API requires using Parser(Language) for the new version
        parser = tree_sitter.Parser(self.languages[lang])
        return parser.parse(source_code)

    def query(self, tree: tree_sitter.Tree, lang: str, query_string: str) -> list[tuple[tree_sitter.Node, str]]:
        """
        Executes AST queries based on S-expressions and QueryCursor.
        
        Args:
            tree: AST Tree to query.
            lang: Language the AST tree belongs to.
            query_string: S-expression query string (using tree-sitter query syntax).
            
        Returns:
            list[tuple[tree_sitter.Node, str]]: List containing (node, capture_name)
                                                sorted by order of appearance (byte order) in the code.
        """
        if lang not in self.languages:
            raise ValueError(f"Language '{lang}' is not supported yet.")

        language = self.languages[lang]
        ts_query = tree_sitter.Query(language, query_string)
        cursor = tree_sitter.QueryCursor(ts_query)

        # cursor.matches(root_node) returns an array of tuples containing (pattern_idx, captures_dict)
        # Where captures_dict is a mapping { "capture_name": [Node, Node, ...] }
        results = []
        for _pattern_index, captures in cursor.matches(tree.root_node):
            for capture_name, nodes in captures.items():
                for node in nodes:
                    results.append((node, capture_name))

        # Sort to ensure order matches their appearance in the source code
        results.sort(key=lambda x: x[0].start_byte)
        return results

    def visualize(self, node: tree_sitter.Node, source_code: bytes, level: int = 0) -> str:
        """
        Recursively prints the AST structure to display a tree visually in directory format.
        Will print actual text (raw text including whitespace, punctuation)
        if it is a leaf node (no children).
        
        Args:
            node: Node to start traversal.
            source_code: Original source bytes to extract leaf node texts.
            level: Branching depth to indent the tree structure.
            
        Returns:
            str: AST structure represented as a string.
        """
        if level == 0:
            indent = ""
        else:
            # Add piping logic to create directory layout
            indent = "│   " * (level - 1) + "├── "

        text_info = ""
        # If there are no children (leaf node), extract raw string to print 100% detail
        if len(node.children) == 0:
            raw_node_text = source_code[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
            text_info = f" {repr(raw_node_text)}"

        node_str = f"{indent}{node.type}{text_info}\n"
        
        for child in node.children:
            node_str += self.visualize(child, source_code, level + 1)

        return node_str

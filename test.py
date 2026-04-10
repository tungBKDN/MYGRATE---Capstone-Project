import json
import sys

# BẪY 1: Kiểm tra xem file có thực sự được chạy không
print(f">>> BẮT ĐẦU CHẠY FILE TẠI: {sys.argv[0]} <<<")

try:
    from tree_sitter import Language, Parser, Node
    import tree_sitter_python as tspython

    print(">>> ĐÃ IMPORT THÀNH CÔNG TREE-SITTER <<<")

    def node_to_dict(node: Node, source_code: bytes) -> dict:
        node_data = {
            "type": node.type,
            "children": []
        }
        if len(node.children) == 0:
            node_data["text"] = source_code[node.start_byte:node.end_byte].decode('utf-8')
        for child in node.children:
            node_data["children"].append(node_to_dict(child, source_code))
        return node_data

    parser = Parser(Language(tspython.language()))
    source = b"def add(a, b): return a + b"
    tree = parser.parse(source)

    print(">>> ĐÃ PARSE XONG CÂY AST <<<")

    ast_json = node_to_dict(tree.root_node, source)

    print("\n" + "="*40)
    print("KẾT QUẢ JSON:")
    print("="*40)
    print(json.dumps(ast_json, indent=2))

except Exception as e:
    # BẪY 2: Nếu có lỗi gì xảy ra, in thẳng ra màn hình chứ không chết ngầm
    print(f"\n!!! LỖI RỒI: {e}")
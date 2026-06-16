import yaml
import json
import os
import glob
import uuid

def extract_rewrite_rules_v2(yaml_dir="."):
    extracted_rules = []

    for file_path in glob.glob(os.path.join(yaml_dir, "*.yml")):
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                docs = yaml.safe_load_all(f)
                for doc in docs:
                    if not doc or 'recipeList' not in doc:
                        continue

                    # 1. BÓC TÁCH METADATA (Phiên bản đích & Lý do)
                    tags = doc.get('tags', [])
                    # Tìm tag chứa chữ 'java' (vd: java17, java11) hoặc mặc định là 'unknown'
                    target_version = next((t for t in tags if 'java' in t or 'jakarta' in t), "general")

                    # Lấy mô tả để làm comment cho Agent hiểu ngữ cảnh
                    description = doc.get('description', '').strip().replace('\n', ' ')

                    # 2. XỬ LÝ TỪNG LUẬT BÊN TRONG VÀ GẮN METADATA VÀO
                    for recipe in doc['recipeList']:
                        if isinstance(recipe, str):
                            continue # Bỏ qua các string ref (như gọi lại luật cũ)

                        rule_data = {
                            "rule_id": str(uuid.uuid4())[:8],
                            "target_version": target_version,
                            "reason": description
                        }

                        # -- Bắt luật đổi Package (VD: com.sun.net.ssl -> javax.net.ssl)
                        if 'org.openrewrite.java.ChangePackage' in recipe:
                            r = recipe['org.openrewrite.java.ChangePackage']
                            rule_data.update({
                                "target": r.get('oldPackageName'),
                                "new": r.get('newPackageName'),
                                "type": "import_declaration",
                                "action": "replace"
                            })
                            extracted_rules.append(rule_data)

                        # -- Bắt luật đổi Method
                        elif 'org.openrewrite.java.ChangeMethodName' in recipe:
                            r = recipe['org.openrewrite.java.ChangeMethodName']
                            rule_data.update({
                                "target": r.get('methodPattern'),
                                "new": r.get('newMethodName'),
                                "type": "method_invocation",
                                "action": "replace"
                            })
                            extracted_rules.append(rule_data)

                        # -- Bắt luật xóa Method (VD: Thread.countStackFrames)
                        elif 'org.openrewrite.java.RemoveMethodInvocations' in recipe:
                            r = recipe['org.openrewrite.java.RemoveMethodInvocations']
                            rule_data.update({
                                "target": r.get('methodPattern'),
                                "new": None,
                                "type": "method_invocation",
                                "action": "delete"
                            })
                            extracted_rules.append(rule_data)

                        # -- Bắt luật đổi Static Target (VD: ToolProvider() -> ToolProvider)
                        elif 'org.openrewrite.java.ChangeMethodTargetToStatic' in recipe:
                            r = recipe['org.openrewrite.java.ChangeMethodTargetToStatic']
                            rule_data.update({
                                "target": r.get('methodPattern'),
                                "new": r.get('fullyQualifiedTargetTypeName'),
                                "type": "object_creation_expression",
                                "action": "change_to_static"
                            })
                            extracted_rules.append(rule_data)

            except Exception as e:
                print(f"Lỗi đọc file {file_path}: {e}")

    # Xuất file
    with open('migration_rules.json', 'w', encoding='utf-8') as f:
        json.dump({"rules": extracted_rules}, f, indent=4, ensure_ascii=False)

    print(f"DONE! Đã trích xuất {len(extracted_rules)} luật có kèm phiên bản đích.")
# Chạy script
if __name__ == "__main__":
    extract_rewrite_rules_v2("D:\capstone_project\MYGRATE---Capstone-Project\src\data_distillation\openrewrite")
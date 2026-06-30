import json
import os
from pathlib import Path

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.models.state import GlobalState
from src.agents.supervisor import get_supervisor_node
from src.agents.reader_agent import ReaderAgent
from src.agents.architect_agent import ArchitectAgent
from src.agents.translator_agent import TranslatorAgent


# --- Wrapper Nodes ---

def architect_node(state: GlobalState):
    """Architect: run initial project index (if not done yet), then run the full 7-step dependency pipeline and candidate review."""
    project_path = state.get("project_path", "")
    target_java = state.get("target_java_version", "17")
    
    # 1. Run lightweight index programmatically if dependencies are missing
    dependencies = state.get("dependencies", [])
    project_type = state.get("project_type")
    
    if not dependencies or not project_type:
        from src.tools.maven_upgrade_tools import index_java_project
        print(f"-> [ARCHITECT] Running programmatic initial project scan...")
        scan_res = index_java_project(project_path)
        if scan_res.get("status") == "ok":
            dependencies = scan_res.get("dependencies", [])
            project_type = scan_res.get("project_type", "java")
        else:
            dependencies = []
            project_type = "java"

    # Check for pre-calculated reports in prerun_architectures or target workspace
    mygrate_root = Path(__file__).resolve().parent.parent
    prerun_dir = mygrate_root / "prerun_architectures" / Path(project_path).name
    report_path = prerun_dir / "upgrade_report.json"
    
    # Fallback to local artifacts_dir in case it was already copied/created
    artifacts_dir = Path(project_path) / "test" / "artifacts"
    if not report_path.exists():
        report_path = artifacts_dir / "upgrade_report.json"
    
    if report_path.exists():
        print(f"-> [ARCHITECT] Found pre-calculated upgrade report at {report_path}. Loading it directly...")
        try:
            with open(report_path, "r", encoding="utf-8") as f:
                upgrade_report = json.load(f)
                
            # Perform final candidate review programmatically
            review_res = None
            try:
                from src.agents.reader_agent import ReaderAgent
                payload = {
                    "project_path": project_path,
                    "project_type": project_type,
                    "target_java": target_java,
                    "dependencies": dependencies,
                    "candidates": upgrade_report.get("candidates", {}),
                    "solutions": upgrade_report.get("solutions", []),
                    "smoke_test_results": upgrade_report.get("smoke_test_results", []),
                    "solver_method": upgrade_report.get("solver_method", "z3"),
                    "step3_reports": {
                        k: {"analysis": {"compatibility_status": v.get("analysis", {}).get("compatibility_status")}}
                        for k, v in upgrade_report.get("step3_reports", {}).items()
                        if isinstance(v, dict)
                    }
                }
                print(f"-> [ARCHITECT] Running final candidate review...")
                review_agent = ReaderAgent()
                review_res = review_agent.review_candidates(payload)
                
                # Write reports to artifacts folder
                artifacts_dir.mkdir(parents=True, exist_ok=True)
                with open(artifacts_dir / "reader_review.json", "w", encoding="utf-8") as f:
                    json.dump(review_res, f, ensure_ascii=False, indent=2, default=str)
                md_content = review_res.get("markdown_report")
                if md_content:
                    with open(artifacts_dir / "reader_review.md", "w", encoding="utf-8") as f:
                        f.write(md_content)
            except Exception as e:
                print(f"Warning: Failed to run candidate review in Architect: {e}")
                
            # Prune step3_reports and conflict_edges to prevent context token length limit exceeded errors in subsequent nodes
            upgrade_report.pop("step3_reports", None)
            upgrade_report.pop("conflict_edges", None)
            
            update = {
                "last_subagent_result": json.dumps(upgrade_report, ensure_ascii=False, indent=2, default=str),
                "project_type": project_type,
                "dependencies": dependencies,
                "candidate_solutions": upgrade_report.get("solutions"),
                "upgrade_report": upgrade_report
            }
            if review_res:
                update["reader_review"] = review_res
                
            return update
        except Exception as e:
            print(f"Warning: Failed to load pre-calculated reports: {e}. Running from scratch...")

    # 2. Run the full 7-step upgrade analysis
    user_feedback = state.get("current_instruction", "")
    full_instruction = (
        f"Dependencies: {json.dumps(dependencies)}\n"
        f"Target Java Version: {target_java}\n"
        f"User Ràng buộc/Chỉ thị từ người dùng (HiTL): {user_feedback}\n"
        f"Nhiệm vụ: Run the full upgrade pipeline to find compatible combinations."
    )

    agent = ArchitectAgent()
    result = agent.run(full_instruction)
    
    # Base updates
    update = {
        "last_subagent_result": result,
        "project_type": project_type,
        "dependencies": dependencies
    }

    try:
        parsed = json.loads(result)
        if isinstance(parsed, dict):
            if parsed.get("solutions"):
                update["candidate_solutions"] = parsed.get("solutions")
            update["upgrade_report"] = parsed

            # 3. Perform final candidate review programmatically
            try:
                from src.agents.reader_agent import ReaderAgent
                payload = {
                    "project_path": project_path,
                    "project_type": project_type,
                    "target_java": target_java,
                    "dependencies": dependencies,
                    "candidates": parsed.get("candidates", {}),
                    "solutions": parsed.get("solutions", []),
                    "smoke_test_results": parsed.get("smoke_test_results", []),
                    "solver_method": parsed.get("solver_method", "z3"),
                    "step3_reports": {
                        k: {"analysis": {"compatibility_status": v.get("analysis", {}).get("compatibility_status")}}
                        for k, v in parsed.get("step3_reports", {}).items()
                        if isinstance(v, dict)
                    }
                }
                print(f"-> [ARCHITECT] Running final candidate review...")
                review_agent = ReaderAgent()
                review_res = review_agent.review_candidates(payload)
                update["reader_review"] = review_res
                
                # Write reports to artifacts folder
                artifacts_dir = Path(project_path) / "test" / "artifacts"
                artifacts_dir.mkdir(parents=True, exist_ok=True)
                with open(artifacts_dir / "reader_review.json", "w", encoding="utf-8") as f:
                    json.dump(review_res, f, ensure_ascii=False, indent=2, default=str)
                md_content = review_res.get("markdown_report")
                if md_content:
                    with open(artifacts_dir / "reader_review.md", "w", encoding="utf-8") as f:
                        f.write(md_content)
            except Exception as e:
                print(f"Warning: Failed to run candidate review in Architect: {e}")

            # Prune step3_reports and conflict_edges to save context window size
            parsed.pop("step3_reports", None)
            parsed.pop("conflict_edges", None)
            update["upgrade_report"] = parsed
    except Exception as e:
        print(f"Warning: Failed to parse ArchitectAgent result: {e}")

    return update

def translator_node(state: GlobalState):
    """Translator: run jdeprscan pipeline first, then apply code transformations."""
    instruction_payload = {
        "project_path": state.get("project_path", ""),
        "target_java_version": state.get("target_java_version", "17"),
        "project_type": state.get("project_type"),
        "current_instruction": state.get("current_instruction", ""),
        "migration_tasks": state.get("migration_tasks", []),
        "jdeprscan_report": state.get("jdeprscan_report"),
        "baseline_coverage": state.get("baseline_coverage", 0.0),
        "baseline_total_tests": state.get("baseline_total_tests", 0),
        "baseline_passed_tests": state.get("baseline_passed_tests", 0),
        "upgrade_report": state.get("upgrade_report"),
        "reader_review": state.get("reader_review"),
    }
    # Pass the previously generated plan and notes if available (from PLAN phase)
    last_res = state.get("last_subagent_result", "")
    if last_res:
        try:
            parsed_res = json.loads(last_res)
            if isinstance(parsed_res, dict):
                inner_ans = parsed_res.get("final_answer") or parsed_res
                if isinstance(inner_ans, dict):
                    instruction_payload["proposed_plan"] = inner_ans.get("markdown_report")
                    instruction_payload["migration_notes"] = inner_ans.get("migration_notes")
        except Exception:
            pass

    agent = TranslatorAgent()
    result = agent.run(json.dumps(instruction_payload, ensure_ascii=False, indent=2, default=str))

    # Check if overall success was achieved from central eval_{model}.json (all 3 gates pass)
    overall_success = True
    failure_reason = ""
    try:
        model_slug = os.getenv("OLLAMA_MODEL", os.getenv("GROQ_MODEL", "default")).replace(":", "_").replace("/", "_")
        mygrate_root = Path(__file__).resolve().parent.parent
        eval_file = mygrate_root / f"eval_{model_slug}.json"
        if eval_file.exists():
            with open(eval_file, "r", encoding="utf-8") as f:
                eval_data = json.load(f)
                codebase_name = Path(state.get("project_path", "")).name
                if codebase_name in eval_data:
                    project_eval = eval_data[codebase_name]
                    overall_success = project_eval.get("overall_success", True)
                    
                    # Gather details of failure steps
                    failures = []
                    if not project_eval.get("compilation_success", True):
                        failures.append("Gate 1 (Compilation Failure)")
                    if not project_eval.get("gate2_tests_pass", True):
                        failures.append(f"Gate 2 (Test Failure: passed {project_eval.get('passed_tests')}/{project_eval.get('total_tests')} tests, expected 100% pass)")
                    if not project_eval.get("gate3_coverage_ok", True):
                        failures.append(f"Gate 3 (Coverage Drop Failure: baseline {project_eval.get('baseline_coverage')}% to current {project_eval.get('line_coverage')}%, drop {project_eval.get('coverage_drop_pp')}pp exceeds 5.0pp threshold)")
                    
                    if failures:
                        failure_reason = " | ".join(failures)
    except Exception as e:
        print(f"Warning: Failed to parse evaluation data: {e}")

    # If compilation or verification failed, do not set translator_completed to True.
    # This allows the Supervisor LLM to route back to Architect for alternative dependency solutions.
    # Also, only set completed to True if the current node run was actually in APPLY mode.
    current_inst = state.get("current_instruction", "")
    is_apply = current_inst.startswith("APPLY:")
    
    run_count = (state.get("translator_run_count") or 0)
    plan_run_count = (state.get("translator_plan_run_count") or 0)
    
    if is_apply:
        run_count += 1
    else:
        plan_run_count += 1
        
    translator_completed = overall_success if is_apply else True
    
    if is_apply and not overall_success and run_count >= 1:
        print(f"-> [WORKFLOW] Max Translator APPLY attempts reached ({run_count}). Terminating to avoid infinite loops.")
        translator_completed = True
        
    if not is_apply and plan_run_count >= 2:
        print(f"-> [WORKFLOW] Max Translator PLAN attempts reached ({plan_run_count}). Terminating plan phase to avoid loops.")
        translator_completed = True

    # If it failed, append failure details to result so supervisor gets the message
    if is_apply and not overall_success:
        try:
            parsed_res = json.loads(result)
            if isinstance(parsed_res, dict):
                parsed_res["status"] = "error"
                parsed_res["error_message"] = f"APPLY mode verification failed: {failure_reason}"
                result = json.dumps(parsed_res, ensure_ascii=False, indent=2, default=str)
        except Exception:
            result = f"Error: APPLY mode verification failed: {failure_reason}\n\nOriginal result: {result}"

    update = {
        "last_subagent_result": result,
        "translator_completed": translator_completed,
        "translator_run_count": run_count,
        "translator_plan_run_count": plan_run_count
    }

    # Extract jdeprscan report from translator result and store in state
    try:
        parsed = json.loads(result)
        if isinstance(parsed, dict):
            report = parsed.get("jdeprscan") or parsed.get("run_jdeprscan")
            if report:
                update["jdeprscan_report"] = report
            
            # Print migration plan / report
            translator_report = parsed.get("markdown_report") or parsed.get("final_answer", {}).get("markdown_report")
            if translator_report:
                print("\n\033[32m\033[1m=== TRANSLATOR MIGRATION REPORT ===\033[0m")
                print(translator_report)
                print("\033[32m\033[1m====================================\033[0m\n")
            notes = parsed.get("migration_notes") or parsed.get("final_answer", {}).get("migration_notes")
            if notes:
                print(f"\033[33m\033[1mMigration Notes:\033[0m\n{notes}\n")
    except Exception:
        pass

    return update


# --- Build Graph ---

def build_app(interrupt: bool = True):
    """Build the LangGraph workflow.

    Args:
        interrupt: If True, pause before each supervisor turn (human-in-the-loop).
                   If False, pipeline runs end-to-end without pauses (for testing/batch).
    """
    workflow = StateGraph(GlobalState)

    workflow.add_node("supervisor", get_supervisor_node)
    workflow.add_node("architect", architect_node)
    workflow.add_node("translator", translator_node)

    workflow.set_entry_point("supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        lambda x: x["next_node"],
        {
            "architect": "architect",
            "translator": "translator",
            "end": END,
            "supervisor": "supervisor",
        },
    )

    workflow.add_edge("architect", "supervisor")
    workflow.add_edge("translator", "supervisor")

    if interrupt:
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory, interrupt_before=["supervisor"])
    else:
        return workflow.compile()


# Default: human-in-the-loop mode
app = build_app(interrupt=True)

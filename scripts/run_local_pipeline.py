"""
Local pipeline runner (deprecated features removed)

The dependency analysis and version-resolution components have been removed from
this codebase. This script now acts as a placeholder to avoid runtime import
errors. To re-enable advanced dependency analysis, restore the removed
modules and their implementations.
"""

import sys

def run(target_root: str = 'freshbrew_data/cantor'):
    print("[run_local_pipeline] Dependency analysis features have been removed from this workspace.")
    print("If you need to run a local scan, use the Reader agent or restore the dependency tools.")
    return 0

if __name__ == '__main__':
    tgt = sys.argv[1] if len(sys.argv) > 1 else 'freshbrew_data/cantor'
    sys.exit(run(tgt))

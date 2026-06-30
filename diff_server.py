import os
import sys
import json
import urllib.parse
import difflib
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = 8080

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MYGRATE - Code Diff Explorer</title>
    <!-- Google Fonts -->
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <!-- Diff2Html CSS -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/diff2html/3.4.48/diff2html.min.css" integrity="sha512-40V5n1L0mGz16sU1T0I56T39Tsd4E/oJpP4pX9sI7hA9f5O16V/oX8bN35lK0k10P/U3u7I9bY1f9Nl5U6k1Aw==" crossorigin="anonymous" referrerpolicy="no-referrer" />
    <style>
        :root {
            --bg-darker: #0d1117;
            --bg-dark: #161b22;
            --bg-light: #21262d;
            --border-color: #30363d;
            --text-main: #c9d1d9;
            --text-muted: #8b949e;
            --accent-blue: #58a6ff;
            --accent-green: #3fb950;
            --accent-orange: #d29922;
            --accent-red: #f85149;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        body {
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-darker);
            color: var(--text-main);
            height: 100vh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }

        header {
            background-color: var(--bg-dark);
            border-bottom: 1px solid var(--border-color);
            padding: 12px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            z-index: 10;
        }

        .logo-section h1 {
            font-size: 20px;
            font-weight: 600;
            color: var(--accent-blue);
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .project-selector {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        select {
            background-color: var(--bg-light);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 8px 16px;
            border-radius: 6px;
            font-family: inherit;
            font-size: 14px;
            outline: none;
            cursor: pointer;
            min-width: 250px;
        }

        select:focus {
            border-color: var(--accent-blue);
        }

        .view-controls {
            display: flex;
            background-color: var(--bg-light);
            border-radius: 6px;
            padding: 2px;
            border: 1px solid var(--border-color);
        }

        .control-btn {
            background: none;
            border: none;
            color: var(--text-muted);
            padding: 6px 12px;
            font-size: 13px;
            font-weight: 500;
            border-radius: 4px;
            cursor: pointer;
            font-family: inherit;
            transition: all 0.2s;
        }

        .control-btn.active {
            background-color: var(--bg-darker);
            color: var(--text-main);
        }

        main {
            display: flex;
            flex: 1;
            overflow: hidden;
        }

        .sidebar {
            width: 320px;
            background-color: var(--bg-dark);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            overflow-y: auto;
        }

        .sidebar-header {
            padding: 16px;
            font-size: 13px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            border-bottom: 1px solid var(--border-color);
        }

        .file-list {
            list-style: none;
            flex: 1;
            padding: 8px 0;
        }

        .file-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 16px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.2s;
            border-left: 3px solid transparent;
        }

        .file-item:hover {
            background-color: var(--bg-light);
        }

        .file-item.active {
            background-color: var(--bg-light);
            border-left-color: var(--accent-blue);
        }

        .file-info {
            display: flex;
            flex-direction: column;
            gap: 2px;
            overflow: hidden;
            white-space: nowrap;
        }

        .file-name {
            font-family: 'JetBrains Mono', monospace;
            font-size: 13px;
            text-overflow: ellipsis;
            overflow: hidden;
        }

        .file-path {
            font-size: 11px;
            color: var(--text-muted);
            text-overflow: ellipsis;
            overflow: hidden;
        }

        .status-badge {
            font-size: 10px;
            font-weight: 600;
            padding: 2px 6px;
            border-radius: 4px;
            text-transform: uppercase;
        }

        .status-modified {
            background-color: rgba(210, 153, 34, 0.15);
            color: var(--accent-orange);
            border: 1px solid rgba(210, 153, 34, 0.2);
        }

        .status-new {
            background-color: rgba(63, 185, 80, 0.15);
            color: var(--accent-green);
            border: 1px solid rgba(63, 185, 80, 0.2);
        }

        .status-deleted {
            background-color: rgba(248, 81, 73, 0.15);
            color: var(--accent-red);
            border: 1px solid rgba(248, 81, 73, 0.2);
        }

        .content-area {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            background-color: var(--bg-darker);
        }

        .diff-viewer {
            flex: 1;
            overflow-y: auto;
            padding: 24px;
        }

        /* Customize Diff2Html output to fit dark theme */
        .d2h-wrapper {
            background-color: var(--bg-dark) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 8px !important;
            color: var(--text-main) !important;
            font-family: 'JetBrains Mono', monospace !important;
        }

        .d2h-file-header {
            background-color: var(--bg-light) !important;
            border-bottom: 1px solid var(--border-color) !important;
            color: var(--text-main) !important;
        }

        .d2h-file-name-wrapper {
            font-size: 14px !important;
        }

        .d2h-code-line, .d2h-code-side-line {
            font-size: 13px !important;
        }

        .d2h-del {
            background-color: rgba(248, 81, 73, 0.15) !important;
        }

        .d2h-ins {
            background-color: rgba(63, 185, 80, 0.15) !important;
        }

        .d2h-code-line-ctn {
            color: inherit !important;
        }

        .empty-state {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            height: 100%;
            color: var(--text-muted);
            gap: 12px;
        }

        .empty-state svg {
            width: 48px;
            height: 48px;
            fill: currentColor;
            opacity: 0.5;
        }

        .empty-state p {
            font-size: 16px;
        }
    </style>
</head>
<body>
    <header>
        <div class="logo-section">
            <h1>
                <svg viewBox="0 0 16 16" width="20" height="20" aria-hidden="true" fill="currentColor"><path d="M1.75 2h12.5a.75.75 0 0 1 .75.75v10.5a.75.75 0 0 1-.75.75H1.75a.75.75 0 0 1-.75-.75V2.75A.75.75 0 0 1 1.75 2Zm12.5 1.5H1.75v9h12.5v-9Zm-9.28 1.47a.75.75 0 0 1 1.06 0L8 6.94l2.97-2.97a.75.75 0 1 1 1.06 1.06L9.06 8l2.97 2.97a.75.75 0 1 1-1.06 1.06L8 9.06l-2.97 2.97a.75.75 0 0 1-1.06-1.06L6.94 8 3.97 5.03a.75.75 0 0 1 0-1.06Z"></path></svg>
                MYGRATE Code Diff Explorer
            </h1>
        </div>
        <div class="project-selector">
            <select id="project-dropdown" onchange="loadProjectFiles()">
                <option value="">-- Select Active Project --</option>
            </select>
            <div class="view-controls">
                <button class="control-btn active" id="btn-side" onclick="changeDiffFormat('side-by-side')">Side-by-Side</button>
                <button class="control-btn" id="btn-line" onclick="changeDiffFormat('line-by-line')">Line-by-Line</button>
            </div>
        </div>
    </header>
    <main>
        <div class="sidebar">
            <div class="sidebar-header">Changed Files</div>
            <ul class="file-list" id="file-tree-container">
                <!-- Dynamic files -->
            </ul>
        </div>
        <div class="content-area">
            <div class="diff-viewer" id="diff-content">
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                    <p>Select a codebase and file to view migrations & changes.</p>
                </div>
            </div>
        </div>
    </main>

    <!-- Highlight.js for Syntax Highlighting -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github-dark.min.css">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>

    <!-- Diff2Html JS -->
    <script type="text/javascript" src="https://cdn.jsdelivr.net/npm/diff2html/bundles/js/diff2html.min.js"></script>
    <script type="text/javascript" src="https://cdn.jsdelivr.net/npm/diff2html/bundles/js/diff2html-ui.min.js"></script>
    <script>
        let currentProject = "";
        let currentFile = "";
        let diffFormat = "side-by-side";

        // Fetch project list on load
        async function fetchProjects() {
            try {
                const res = await fetch('/api/projects');
                const data = await res.json();
                const dropdown = document.getElementById('project-dropdown');
                
                // Reset dropdown
                dropdown.innerHTML = '<option value="">-- Select Active Project --</option>';
                data.projects.forEach(p => {
                    const opt = document.createElement('option');
                    opt.value = p;
                    opt.textContent = p;
                    dropdown.appendChild(opt);
                });
            } catch(e) {
                console.error("Error loading projects", e);
            }
        }

        async function loadProjectFiles() {
            const dropdown = document.getElementById('project-dropdown');
            currentProject = dropdown.value;
            currentFile = "";
            
            const container = document.getElementById('file-tree-container');
            container.innerHTML = '';
            
            const diffContent = document.getElementById('diff-content');
            diffContent.innerHTML = `
                <div class="empty-state">
                    <p>Loading changed files...</p>
                </div>`;
            
            if(!currentProject) {
                diffContent.innerHTML = `
                    <div class="empty-state">
                        <p>Select a codebase and file to view migrations & changes.</p>
                    </div>`;
                return;
            }

            try {
                const res = await fetch(`/api/files?project=${encodeURIComponent(currentProject)}`);
                const data = await res.json();
                
                if (data.files.length === 0) {
                    container.innerHTML = '<li class="file-item" style="color: var(--text-muted); cursor: default;">No changed files found</li>';
                    diffContent.innerHTML = `
                        <div class="empty-state">
                            <p>No changes detected vs baseline repository.</p>
                        </div>`;
                    return;
                }

                data.files.forEach(f => {
                    const li = document.createElement('li');
                    li.className = 'file-item';
                    li.onclick = () => selectFile(f.rel_path, li);
                    
                    const badgeClass = f.status === 'new' ? 'status-new' : (f.status === 'deleted' ? 'status-deleted' : 'status-modified');
                    
                    li.innerHTML = `
                        <div class="file-info">
                            <span class="file-name">${f.name}</span>
                            <span class="file-path">${f.rel_path}</span>
                        </div>
                        <span class="status-badge ${badgeClass}">${f.status}</span>
                    `;
                    container.appendChild(li);
                });

                diffContent.innerHTML = `
                    <div class="empty-state">
                        <p>Select a file to inspect differences.</p>
                    </div>`;
            } catch(e) {
                console.error(e);
            }
        }

        async function selectFile(relPath, element) {
            currentFile = relPath;
            
            // Remove active classes
            document.querySelectorAll('.file-item').forEach(el => el.classList.remove('active'));
            element.classList.add('active');
            
            renderDiff();
        }

        async function renderDiff() {
            if(!currentProject || !currentFile) return;

            const diffContent = document.getElementById('diff-content');
            diffContent.innerHTML = '<div class="empty-state"><p>Generating diff...</p></div>';

            try {
                const res = await fetch(`/api/diff?project=${encodeURIComponent(currentProject)}&file=${encodeURIComponent(currentFile)}`);
                const diffText = await res.text();

                if(!diffText.trim()) {
                    diffContent.innerHTML = '<div class="empty-state"><p>No difference found for this file.</p></div>';
                    return;
                }

                diffContent.innerHTML = '';
                const diffui = new Diff2HtmlUI(diffContent, diffText, {
                    drawFileList: false,
                    matching: 'lines',
                    outputFormat: diffFormat,
                    synchronizedScroll: true,
                    highlight: true
                });
                diffui.draw();
            } catch(e) {
                diffContent.innerHTML = `<div class="empty-state" style="color:var(--accent-red)"><p>Error rendering diff: ${e}</p></div>`;
            }
        }

        function changeDiffFormat(format) {
            diffFormat = format;
            document.getElementById('btn-side').classList.toggle('active', format === 'side-by-side');
            document.getElementById('btn-line').classList.toggle('active', format === 'line-by-line');
            renderDiff();
        }

        fetchProjects();
    </script>
</body>
</html>
"""

class DiffHTTPHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Mute console request logging to avoid cluttering agent run output
        pass

    def do_GET(self):
        url_parsed = urllib.parse.urlparse(self.path)
        path = url_parsed.path
        query = urllib.parse.parse_qs(url_parsed.query)

        # Serve UI Index
        if path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode('utf-8'))
            return

        # API: Projects List
        if path == "/api/projects":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            
            projects = []
            freshbrew_dir = Path("freshbrew_data")
            if freshbrew_dir.exists():
                projects = sorted([d.name for d in freshbrew_dir.iterdir() if d.is_dir() and (d / "pom.xml").exists()])
                
            self.wfile.write(json.dumps({"projects": projects}).encode('utf-8'))
            return

        # API: Files List for selected project
        if path == "/api/files":
            project = query.get("project", [""])[0]
            if not project:
                self.send_error(400, "Missing project param")
                return

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            files = []
            
            # Find working directories
            original_dir = Path("freshbrew_data") / project
            working_root = Path("working")
            
            # Find the working copy
            working_copy = None
            if working_root.exists():
                for model_dir in working_root.iterdir():
                    if model_dir.is_dir():
                        target_dir = model_dir / project
                        if target_dir.exists():
                            working_copy = target_dir
                            break
                            
            if not working_copy:
                # If not copied to working/, compare with original itself (will show no change)
                working_copy = original_dir

            if original_dir.exists() and working_copy.exists():
                # Traverse files recursively
                orig_files = set()
                work_files = set()
                
                for p in original_dir.rglob("*"):
                    if p.is_file() and not any(part in p.parts for part in ["target", ".git"]):
                        orig_files.add(p.relative_to(original_dir).as_posix())
                        
                for p in working_copy.rglob("*"):
                    if p.is_file() and not any(part in p.parts for part in ["target", ".git"]):
                        work_files.add(p.relative_to(working_copy).as_posix())

                all_files = sorted(list(orig_files.union(work_files)))

                for f in all_files:
                    orig_path = original_dir / f
                    work_path = working_copy / f
                    
                    status = None
                    if f not in orig_files:
                        status = "new"
                    elif f not in work_files:
                        status = "deleted"
                    else:
                        # Compare file contents to check if modified
                        try:
                            with open(orig_path, 'r', encoding='utf-8', errors='ignore') as o_f:
                                o_txt = o_f.read()
                            with open(work_path, 'r', encoding='utf-8', errors='ignore') as w_f:
                                w_txt = w_f.read()
                            if o_txt != w_txt:
                                status = "modified"
                        except Exception:
                            status = "modified"

                    if status:
                        files.append({
                            "name": Path(f).name,
                            "rel_path": f,
                            "status": status
                        })

            self.wfile.write(json.dumps({"files": files}).encode('utf-8'))
            return

        # API: Get Diff for selected file
        if path == "/api/diff":
            project = query.get("project", [""])[0]
            rel_file = query.get("file", [""])[0]
            if not project or not rel_file:
                self.send_error(400, "Missing params")
                return

            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()

            original_dir = Path("freshbrew_data") / project
            working_root = Path("working")
            
            # Find working copy
            working_copy = None
            if working_root.exists():
                for model_dir in working_root.iterdir():
                    if model_dir.is_dir():
                        target_dir = model_dir / project
                        if target_dir.exists():
                            working_copy = target_dir
                            break

            if not working_copy:
                working_copy = original_dir

            orig_path = original_dir / rel_file
            work_path = working_copy / rel_file

            orig_lines = []
            work_lines = []

            if orig_path.exists():
                try:
                    with open(orig_path, 'r', encoding='utf-8', errors='ignore') as f:
                        orig_lines = f.readlines()
                except Exception:
                    pass

            if work_path.exists():
                try:
                    with open(work_path, 'r', encoding='utf-8', errors='ignore') as f:
                        work_lines = f.readlines()
                except Exception:
                    pass

            diff = difflib.unified_diff(
                orig_lines,
                work_lines,
                fromfile=f"a/{rel_file}",
                tofile=f"b/{rel_file}",
                lineterm=''
            )
            
            self.wfile.write('\n'.join(diff).encode('utf-8'))
            return

        self.send_error(404, "Not Found")

def main():
    server = HTTPServer(('localhost', PORT), DiffHTTPHandler)
    print(f"============================================================")
    print(f"🚀 MYGRATE Diff Explorer server started at http://localhost:{PORT}")
    print(f"Open http://localhost:{PORT} in your web browser to check modifications.")
    print(f"============================================================")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server...")
        server.server_close()

if __name__ == "__main__":
    main()

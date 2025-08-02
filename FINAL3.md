1. The XRAY Philosophy: The Problem and Solution
When a Large Language Model (LLM) interacts with a codebase, it typically processes one file at a time. This approach lacks the high-level structural context a human developer uses, such as the project's file layout, the location of key definitions, and the relationships between different parts of the code. This can lead to inefficient or incorrect code modifications.

XRAY is designed to provide this missing context. It functions as a structural analysis toolset that gives the LLM a high-level understanding of a codebase through three key pieces of information:

The Map (build_index): A visual layout of the project's file and directory structure.

The Index (find_symbol): A way to locate specific functions, classes, or other symbols using fuzzy, natural language queries.

The Context (what_breaks/what_depends): Tools to analyze a specific piece of code to see what it uses and what other parts of the code use it.

The benefit of this approach is its balance of utility and simplicity. It provides structured, code-aware data that is significantly more useful than raw text search, without incurring the setup and performance overhead of a full language server.

Why ast-grep? (And Not Just grep)
A simpler tool like grep is insufficient for this task because it is not "code-aware."

grep performs text search. A search for a function name like authenticate will return matches from function definitions, variable names, comments, and documentation strings. This output is noisy and unreliable for code analysis.

ast-grep performs structural search. It is powered by tree-sitter and parses code to understand its syntax. A search for a function authenticate will only match the def authenticate(...): or function authenticate(...) structure, ignoring irrelevant text matches.

This structural approach provides the clean and accurate results necessary for the XRAY tools to function reliably.

2. Core Philosophy: On-Demand Structural Analysis
This plan is built on a simple, powerful workflow. We will use ast-grep as a single-binary analysis engine to perform live, on-demand structural analysis. There is no complex, persistent index of symbols. The tools follow a strict sequence to provide the LLM with context.

Workflow: build_index (to see the file layout) -> find_symbol (to locate specific code) -> what_depends/what_breaks (to analyze that specific code).

Pathing: All tools that interact with the file system require the absolute path to the project's root directory. The XRAY server will not guess or resolve relative paths.

Dependency: The only external dependency is the ast-grep command-line tool.

3. Tool Implementation Details
build_index(root_path)
This tool's only purpose is to give the LLM a visual map of the repository's file structure. It does not analyze file contents.

Input: root_path (string): The absolute path to the project directory.

Action:

Execute a Python script that recursively walks the root_path.

The script must respect rules in .gitignore files and ignore a default set of common directories and file patterns to keep the output clean and relevant.

Default Exclusions:

# Directories
node_modules/      # JavaScript/Node.js dependencies
vendor/            # Go and PHP dependencies
__pycache__/       # Python bytecode cache
venv/              # Python virtual environment
.venv/             # Python virtual environment (alternative name)
env/               # Python virtual environment (another alternative)
target/            # Rust/Java build output
build/             # Generic build output directory
dist/              # Distribution/build output
.git/              # Git version control
.svn/              # Subversion version control
.hg/               # Mercurial version control
.idea/             # IntelliJ IDEA IDE files
.vscode/           # Visual Studio Code IDE files
.xray/             # XRAY's own index directory

# File Patterns
*.pyc              # Python compiled bytecode files
*.log              # Log files
.DS_Store          # macOS finder metadata
Thumbs.db          # Windows thumbnail cache

It will generate a text-based, tree-like representation of the filtered directory structure.

Output: A single string containing the visual directory tree.

Example Output:

/path/to/avocado/
├── app/
│   └── main.py
├── frontend/
├── requirements.txt
└── Dockerfile

find_symbol(root_path, query)
This is the primary analysis tool. It performs a live, fuzzy search for symbol definitions and returns structured objects representing the best matches.

Input:

root_path (string): The absolute path to the project directory.

query (string): The fuzzy search term from the user (e.g., "auth service").

Action:

Broad Search: Run a single, comprehensive ast-grep rule across the entire root_path to find all possible symbol definitions. This is best done with a YAML configuration file.

Collect Candidates: Parse the JSON output from ast-grep to create a list of all symbol names found.

Fuzzy Match: Use a Python library like thefuzz to score the similarity between the user's query and each candidate name.

Output: A list of the top 5-10 matching "Exact Symbol" objects. Each object is a dictionary containing all the information needed for subsequent tools:

[
  {
    "name": "authenticate_user",
    "type": "function",
    "path": "/path/to/avocado/app/main.py",
    "start_line": 55,
    "end_line": 72
  },
  ...
]

what_depends(exact_symbol)
This tool answers: "What does this specific piece of code use?" It takes the direct output from find_symbol.

Input: exact_symbol (object): A single "Exact Symbol" object returned by find_symbol.

Action:

Extract the path, start_line, and end_line from the input object.

Run a live, scoped ast-grep scan on that single path. Since ast-grep doesn't have a line-range flag, you will first read the file, extract the relevant lines of code into a string, and then pass that string to ast-grep for analysis.

The ast-grep patterns will search for usage patterns like function calls (pattern: "$CALL($_)") and imports (pattern: "import $MODULE").

Output: A list of names of dependencies (functions called, modules imported) found within that specific code block.

what_breaks(exact_symbol)
This tool provides a best-effort impact analysis based on a symbol's name.

Input: exact_symbol (object): A single "Exact Symbol" object returned by find_symbol.

Action:

Extract the name (e.g., "authenticate_user") and the root_path from the input object's path.

Run a global ast-grep search across the entire root_path.

The command will be highly specific, searching for all call sites that match the exact name (e.g., ast-grep --pattern "authenticate_user($_)" --json /path/to/root).

Output: A list of all locations (file path and line number) where that symbol name is used. The output must include the standard caveat:

"Found X potential call sites. Note: This search is based on the symbol's name and may include references to other items with the same name in different modules."

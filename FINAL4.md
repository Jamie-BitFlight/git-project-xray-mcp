1. The XRAY Philosophy: A New Vision
The goal of XRAY is to provide an LLM with just enough context to navigate and modify a codebase intelligently. This revised plan simplifies the toolset to three core functions that follow a natural, intuitive workflow for code exploration and modification.

Map (explore_repo): Get a high-level overview of the repository structure, including a "skeleton" of what's inside each file.

Find (find_symbol): Use a fuzzy query to locate a specific piece of code.

Impact (what_breaks): Once a symbol is found, perform a quick, best-effort search to see where it's used.

This approach is a hybrid model. It uses the best tool for each job: lightweight regex/AST parsing for a quick overview, a powerful structural tool for accurate searching, and a simple text-based tool for rapid impact analysis. This maintains the project's core goal of simplicity while providing significant value over basic file reading.

2. Core Principles
Minimalism: The toolset is reduced to three essential, easy-to-understand functions. The what_depends tool is eliminated.

Progressive Discovery: The LLM is encouraged to first map the terrain (explore_repo), then pinpoint a target (find_symbol), and finally assess the surroundings (what_breaks).

Pragmatic Implementation: We will use the simplest effective technology for each tool, accepting the trade-offs.

3. Tool Implementation Details
Tool 1: explore_repo(root_path, max_symbols_per_file=5)
This tool provides a visual tree of the repository, enriched with a "skeleton" of each file's contents to give the LLM a peek inside without reading the whole file.

Input:

root_path (string): The absolute path to the project directory.

max_symbols_per_file (int, optional): The maximum number of symbol names to show for each file to prevent overwhelming output. Defaults to 5.

Action:

Recursively walk the root_path, respecting .gitignore and the standard list of default exclusions (node_modules, __pycache__, etc.).

For each source file encountered:

Perform a lightweight, top-level-only scan to extract key symbol names. This does not require a full structural tool.

Python: Use the built-in ast module to find top-level ClassDef and FunctionDef nodes. This is fast and accurate.

JS/TS/Go: Use a small set of targeted regular expressions to find keywords like function, class, interface, type, and struct at the beginning of lines.

Limit the results to max_symbols_per_file. If more symbols exist, append a note like "... and 12 more".

Format the output as a single text string representing the file tree with inline skeletons.

Output: A single string containing the visual tree.

Example Output:

/path/to/project/
├── src/
│   ├── auth.py [class AuthService, def authenticate, def validate_token, ... and 1 more]
│   └── models.py [class User, class Session, def get_user_by_id]
└── tests/
    └── test_auth.py [class TestAuth, def test_auth_success, def test_auth_failure]

Tool 2: find_symbol(root_path, query)
This tool is the most powerful and precise in the set, using a structural analyzer for accuracy.

Input:

root_path (string): The absolute path to the project directory.

query (string): The fuzzy search term (e.g., "auth service").

Action:

Use a structural tool (ast-grep or semgrep) to perform a broad search for all possible symbol definitions across the entire project.

Collect all symbol names from the structured output.

Use a fuzzy-matching library (thefuzz) to compare the query against the collected names.

Output: A list of the top-matching "Exact Symbol" objects, each containing the name, type, path, and start/end line numbers.

Tool 3: what_breaks(exact_symbol)
This tool is simplified to be a fast, "good enough" impact analysis using a text-based search.

Input: exact_symbol (object): A single "Exact Symbol" object returned by find_symbol.

Action:

Extract the symbol name and root_path from the input object.

Use a fast grep tool (like ripgrep) or Python's built-in re module to search for the exact symbol name as a whole word across all files in the root_path.

For each match, capture the line number and the line of text.

Output: A list of locations where the symbol name was found. The standard caveat remains critical:

"Found X potential references based on a text search for the name 'authenticate_user'. This may include comments, strings, or other unrelated symbols."

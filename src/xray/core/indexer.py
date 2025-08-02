"""Core indexing engine for XRAY - ast-grep based implementation."""

import os
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
import fnmatch
from thefuzz import fuzz

# Default exclusions
DEFAULT_EXCLUSIONS = {
    # Directories
    "node_modules", "vendor", "__pycache__", "venv", ".venv", "env",
    "target", "build", "dist", ".git", ".svn", ".hg", ".idea", ".vscode",
    ".xray", "site-packages", ".tox", ".pytest_cache", ".mypy_cache",
    
    # File patterns
    "*.pyc", "*.pyo", "*.pyd", "*.so", "*.dll", "*.log", 
    ".DS_Store", "Thumbs.db", "*.swp", "*.swo", "*~"
}


class XRayIndexer:
    """Main indexer for XRAY - provides file tree and symbol extraction using ast-grep."""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path).resolve()
    
    def build_index(self) -> str:
        """
        Build a visual file tree of the repository.
        Returns a formatted tree string.
        """
        # Get gitignore patterns if available
        gitignore_patterns = self._parse_gitignore()
        
        # Build the tree
        tree_lines = []
        self._build_tree_recursive(
            self.root_path, 
            tree_lines, 
            "", 
            gitignore_patterns,
            is_last=True
        )
        
        return "\n".join(tree_lines)
    
    def _parse_gitignore(self) -> Set[str]:
        """Parse .gitignore file if it exists."""
        patterns = set()
        gitignore_path = self.root_path / ".gitignore"
        
        if gitignore_path.exists():
            try:
                with open(gitignore_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            patterns.add(line)
            except Exception:
                pass
        
        return patterns
    
    def _should_exclude(self, path: Path, gitignore_patterns: Set[str]) -> bool:
        """Check if a path should be excluded."""
        name = path.name
        
        # Check default exclusions
        if name in DEFAULT_EXCLUSIONS:
            return True
        
        # Check file pattern exclusions
        for pattern in DEFAULT_EXCLUSIONS:
            if '*' in pattern and fnmatch.fnmatch(name, pattern):
                return True
        
        # Check gitignore patterns (simplified)
        for pattern in gitignore_patterns:
            if pattern in str(path.relative_to(self.root_path)):
                return True
            if fnmatch.fnmatch(name, pattern):
                return True
        
        return False
    
    def _build_tree_recursive(
        self, 
        path: Path, 
        tree_lines: List[str], 
        prefix: str, 
        gitignore_patterns: Set[str],
        is_last: bool = False
    ):
        """Recursively build the tree representation."""
        if self._should_exclude(path, gitignore_patterns):
            return
        
        # Add current item
        name = path.name if path != self.root_path else str(path)
        connector = "└── " if is_last else "├── "
        
        if path == self.root_path:
            tree_lines.append(name)
        else:
            tree_lines.append(prefix + connector + name)
        
        # Only recurse into directories
        if path.is_dir():
            # Get children and sort them
            try:
                children = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
                # Filter out excluded items
                children = [c for c in children if not self._should_exclude(c, gitignore_patterns)]
                
                for i, child in enumerate(children):
                    is_last_child = (i == len(children) - 1)
                    extension = "    " if is_last else "│   "
                    new_prefix = prefix + extension if path != self.root_path else ""
                    
                    self._build_tree_recursive(
                        child, 
                        tree_lines, 
                        new_prefix, 
                        gitignore_patterns,
                        is_last_child
                    )
            except PermissionError:
                pass
    
    def find_symbol(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find symbols matching the query using fuzzy search.
        Uses ast-grep to find all symbols, then fuzzy matches against the query.
        
        Returns a list of the top matching "Exact Symbol" objects.
        """
        all_symbols = []
        
        # Define patterns for different symbol types
        patterns = [
            # Python functions and classes
            ("def $NAME($$$):", "function"),
            ("class $NAME($$$):", "class"),
            ("async def $NAME($$$):", "function"),
            
            # JavaScript/TypeScript functions and classes
            ("function $NAME($$$)", "function"),
            ("const $NAME = ($$$) =>", "function"),
            ("let $NAME = ($$$) =>", "function"),
            ("var $NAME = ($$$) =>", "function"),
            ("class $NAME", "class"),
            ("interface $NAME", "interface"),
            ("type $NAME =", "type"),
            
            # Go functions and types
            ("func $NAME($$$)", "function"),
            ("func ($$$) $NAME($$$)", "method"),
            ("type $NAME struct", "struct"),
            ("type $NAME interface", "interface"),
        ]
        
        # Run ast-grep for each pattern
        for pattern, symbol_type in patterns:
            cmd = [
                "ast-grep",
                "--pattern", pattern,
                "--json",
                str(self.root_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                try:
                    matches = json.loads(result.stdout)
                    for match in matches:
                        # Extract details from match
                        text = match.get("text", "")
                        file_path = match.get("file", "")
                        start = match.get("range", {}).get("start", {})
                        end = match.get("range", {}).get("end", {})
                        
                        # Extract the name from metavariables
                        metavars = match.get("metaVariables", {})
                        name = None
                        
                        # Try to get NAME from metavariables
                        if "NAME" in metavars:
                            name = metavars["NAME"]["text"]
                        else:
                            # Fallback to regex extraction
                            name = self._extract_symbol_name(text)
                        
                        if name:
                            symbol = {
                                "name": name,
                                "type": symbol_type,
                                "path": file_path,
                                "start_line": start.get("line", 1),
                                "end_line": end.get("line", start.get("line", 1))
                            }
                            all_symbols.append(symbol)
                except json.JSONDecodeError:
                    continue
        
        # Deduplicate symbols (same name and location)
        seen = set()
        unique_symbols = []
        for symbol in all_symbols:
            key = (symbol["name"], symbol["path"], symbol["start_line"])
            if key not in seen:
                seen.add(key)
                unique_symbols.append(symbol)
        
        # Now perform fuzzy matching against the query
        scored_symbols = []
        for symbol in unique_symbols:
            # Calculate similarity score
            score = fuzz.partial_ratio(query.lower(), symbol["name"].lower())
            
            # Boost score for exact substring matches
            if query.lower() in symbol["name"].lower():
                score = max(score, 80)
            
            scored_symbols.append((score, symbol))
        
        # Sort by score and take top results
        scored_symbols.sort(key=lambda x: x[0], reverse=True)
        top_symbols = [s[1] for s in scored_symbols[:limit]]
        
        return top_symbols
    
    def _extract_symbol_name(self, text: str) -> Optional[str]:
        """Extract the symbol name from matched text."""
        import re
        
        # Patterns to extract names from different definition types
        patterns = [
            r'(?:def|class|function|interface|type)\s+(\w+)',
            r'(?:const|let|var)\s+(\w+)\s*=',
            r'func\s+(?:\([^)]+\)\s+)?(\w+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _determine_symbol_type(self, text: str) -> str:
        """Determine the type of symbol from the matched text."""
        if 'class' in text:
            return 'class'
        elif 'interface' in text:
            return 'interface'
        elif 'type' in text and ('struct' in text or 'interface' in text):
            return 'type'
        elif 'def' in text or 'function' in text or 'func' in text or '=>' in text:
            return 'function'
        else:
            return 'unknown'
    
    def what_depends(self, exact_symbol: Dict[str, Any]) -> List[str]:
        """
        Find what a symbol depends on (calls/imports).
        Uses ast-grep to analyze the specific code block.
        """
        file_path = exact_symbol['path']
        start_line = exact_symbol['start_line']
        end_line = exact_symbol['end_line']
        
        # Extract the relevant code block
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # Adjust for 0-based indexing
                code_block = ''.join(lines[start_line-1:end_line])
        except Exception:
            return []
        
        # Create patterns to find function calls and imports
        patterns = [
            # Function calls
            "$FUNC($$$)",
            # Import statements
            "import $MODULE",
            "from $MODULE import $$$",
            "import $MODULE from $$$",
            "const $VAR = require($MODULE)",
            "const $VAR = require('$MODULE')",
            'const $VAR = require("$MODULE")',
        ]
        
        dependencies = set()
        
        # Create a temporary file with the code block
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.tmp', delete=False) as f:
            f.write(code_block)
            temp_file = f.name
        
        try:
            for pattern in patterns:
                cmd = [
                    "ast-grep",
                    "--pattern", pattern,
                    "--json",
                    temp_file
                ]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    try:
                        matches = json.loads(result.stdout)
                        for match in matches:
                            # Extract metavariables
                            metavars = match.get("metaVariables", {})
                            
                            # Try to get function name from FUNC
                            if "FUNC" in metavars:
                                dependencies.add(metavars["FUNC"]["text"])
                            
                            # Try to get module name from MODULE
                            if "MODULE" in metavars:
                                dependencies.add(metavars["MODULE"]["text"])
                            
                            # Fallback to text extraction
                            if not metavars:
                                text = match.get("text", "")
                                dep_name = self._extract_dependency_name(text)
                                if dep_name:
                                    dependencies.add(dep_name)
                    except json.JSONDecodeError:
                        pass
        finally:
            os.unlink(temp_file)
        
        return sorted(list(dependencies))
    
    def _extract_dependency_name(self, text: str) -> Optional[str]:
        """Extract dependency name from matched text."""
        import re
        
        # Try to extract function name from calls
        match = re.match(r'(\w+)\s*\(', text)
        if match:
            return match.group(1)
        
        # Try to extract module names from imports
        patterns = [
            r'import\s+(\w+)',
            r'from\s+(\w+)',
            r'require\s*\(\s*["\']([^"\']+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def what_breaks(self, exact_symbol: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find what uses a symbol (reverse dependencies).
        Uses ast-grep to search for calls to the symbol name.
        
        Returns a dictionary with references and a standard caveat.
        """
        symbol_name = exact_symbol['name']
        
        # Create pattern to find calls to this symbol
        cmd = [
            "ast-grep",
            "--pattern", f"{symbol_name}($$$)",
            "--json",
            str(self.root_path)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        references = []
        if result.returncode == 0:
            try:
                matches = json.loads(result.stdout)
                for match in matches:
                    file_path = match.get("file", "")
                    start = match.get("range", {}).get("start", {})
                    
                    references.append({
                        "file": file_path,
                        "line": start.get("line", 1)
                    })
            except json.JSONDecodeError:
                pass
        
        return {
            "references": references,
            "total_count": len(references),
            "note": f"Found {len(references)} potential call sites. Note: This search is based on the symbol's name and may include references to other items with the same name in different modules."
        }
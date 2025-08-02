"""Core indexing engine for XRAY - ast-grep based implementation."""

import os
import re
import ast
import json
import subprocess
import hashlib
import pickle
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Tuple
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

# Language extensions
LANGUAGE_MAP = {
    ".py": "python",
    ".js": "javascript", 
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".go": "go",
}


class XRayIndexer:
    """Main indexer for XRAY - provides file tree and symbol extraction using ast-grep."""
    
    def __init__(self, root_path: str):
        self.root_path = Path(root_path).resolve()
        self._cache = {}
        self._init_cache()
    
    def _init_cache(self):
        """Initialize cache based on git commit SHA."""
        try:
            # Get current git commit SHA
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.root_path,
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                self.commit_sha = result.stdout.strip()
                self.cache_dir = Path(f"/tmp/.xray_cache/{self.commit_sha}")
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                self._load_cache()
            else:
                self.commit_sha = None
                self.cache_dir = None
        except:
            self.commit_sha = None
            self.cache_dir = None
    
    def _load_cache(self):
        """Load cache from disk if available."""
        if not self.cache_dir:
            return
        
        cache_file = self.cache_dir / "symbols.pkl"
        if cache_file.exists():
            try:
                with open(cache_file, 'rb') as f:
                    self._cache = pickle.load(f)
            except:
                self._cache = {}
    
    def _save_cache(self):
        """Save cache to disk."""
        if not self.cache_dir:
            return
        
        cache_file = self.cache_dir / "symbols.pkl"
        try:
            with open(cache_file, 'wb') as f:
                pickle.dump(self._cache, f)
        except:
            pass
    
    def _get_cache_key(self, file_path: Path) -> str:
        """Generate cache key for a file."""
        try:
            stat = file_path.stat()
            return f"{file_path}:{stat.st_mtime}:{stat.st_size}"
        except:
            return str(file_path)
    
    def explore_repo(
        self, 
        max_depth: Optional[int] = None,
        include_symbols: bool = False,
        focus_dirs: Optional[List[str]] = None,
        max_symbols_per_file: int = 5
    ) -> str:
        """
        Build a visual file tree with optional symbol skeletons.
        
        Args:
            max_depth: Limit directory traversal depth
            include_symbols: Include symbol skeletons in output
            focus_dirs: Only include these top-level directories
            max_symbols_per_file: Max symbols to show per file
            
        Returns:
            Formatted tree string
        """
        # Get gitignore patterns if available
        gitignore_patterns = self._parse_gitignore()
        
        # Build the tree
        tree_lines = []
        self._build_tree_recursive_enhanced(
            self.root_path, 
            tree_lines, 
            "", 
            gitignore_patterns,
            current_depth=0,
            max_depth=max_depth,
            include_symbols=include_symbols,
            focus_dirs=focus_dirs,
            max_symbols_per_file=max_symbols_per_file,
            is_last=True
        )
        
        # Save cache after building tree
        if include_symbols:
            self._save_cache()
        
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
    
    def _should_include_dir(self, path: Path, focus_dirs: Optional[List[str]], current_depth: int) -> bool:
        """Check if a directory should be included based on focus_dirs."""
        if not focus_dirs or current_depth > 0:
            return True
        
        # At depth 0 (top-level), only include if in focus_dirs
        return path.name in focus_dirs
    
    def _build_tree_recursive_enhanced(
        self, 
        path: Path, 
        tree_lines: List[str], 
        prefix: str, 
        gitignore_patterns: Set[str],
        current_depth: int,
        max_depth: Optional[int],
        include_symbols: bool,
        focus_dirs: Optional[List[str]],
        max_symbols_per_file: int,
        is_last: bool = False
    ):
        """Recursively build the tree representation with enhanced features."""
        if self._should_exclude(path, gitignore_patterns):
            return
        
        # Check depth limit
        if max_depth is not None and current_depth > max_depth:
            return
        
        # Check focus_dirs for directories
        if path.is_dir() and not self._should_include_dir(path, focus_dirs, current_depth):
            return
        
        # Add current item
        name = path.name if path != self.root_path else str(path)
        connector = "└── " if is_last else "├── "
        
        # For files, add skeleton if requested
        if path.is_file() and include_symbols and path.suffix.lower() in LANGUAGE_MAP:
            skeleton = self._get_file_skeleton_enhanced(path, max_symbols_per_file)
            if skeleton:
                # Format with indented skeleton
                if path == self.root_path:
                    tree_lines.append(name)
                else:
                    tree_lines.append(prefix + connector + name)
                
                # Add skeleton lines
                for i, skel_line in enumerate(skeleton):
                    is_last_skel = (i == len(skeleton) - 1)
                    skel_prefix = prefix + ("    " if is_last else "│   ")
                    skel_connector = "└── " if is_last_skel else "├── "
                    tree_lines.append(skel_prefix + skel_connector + skel_line)
            else:
                # No skeleton, just show filename
                if path == self.root_path:
                    tree_lines.append(name)
                else:
                    tree_lines.append(prefix + connector + name)
        else:
            # Directory or file without symbols
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
                
                # Apply focus_dirs filter at top level
                if current_depth == 0 and focus_dirs:
                    children = [c for c in children if c.is_file() or c.name in focus_dirs]
                
                for i, child in enumerate(children):
                    is_last_child = (i == len(children) - 1)
                    extension = "    " if is_last else "│   "
                    new_prefix = prefix + extension if path != self.root_path else ""
                    
                    self._build_tree_recursive_enhanced(
                        child, 
                        tree_lines, 
                        new_prefix, 
                        gitignore_patterns,
                        current_depth + 1,
                        max_depth,
                        include_symbols,
                        focus_dirs,
                        max_symbols_per_file,
                        is_last_child
                    )
            except PermissionError:
                pass
    
    def _get_file_skeleton_enhanced(self, file_path: Path, max_symbols: int) -> List[str]:
        """Extract enhanced symbol info including signatures and docstrings."""
        # Check cache first
        cache_key = self._get_cache_key(file_path)
        if cache_key in self._cache:
            cached_symbols = self._cache[cache_key]
            return self._format_enhanced_skeleton(cached_symbols, max_symbols)
        
        language = LANGUAGE_MAP.get(file_path.suffix.lower())
        if not language:
            return []
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if language == "python":
                symbols = self._extract_python_symbols_enhanced(content)
            else:
                symbols = self._extract_regex_symbols_enhanced(content, language)
            
            # Cache the results
            self._cache[cache_key] = symbols
            
            return self._format_enhanced_skeleton(symbols, max_symbols)
        
        except Exception:
            return []
    
    def _format_enhanced_skeleton(self, symbols: List[Dict[str, str]], max_symbols: int) -> List[str]:
        """Format enhanced symbol info for display."""
        if not symbols:
            return []
        
        lines = []
        shown_count = min(len(symbols), max_symbols)
        
        for symbol in symbols[:shown_count]:
            line = symbol['signature']
            if symbol.get('doc'):
                line += f" # {symbol['doc']}"
            lines.append(line)
        
        if len(symbols) > max_symbols:
            remaining = len(symbols) - max_symbols
            lines.append(f"... and {remaining} more")
        
        return lines
    
    def _extract_python_symbols_enhanced(self, content: str) -> List[Dict[str, str]]:
        """Extract Python symbols with signatures and docstrings."""
        symbols = []
        try:
            tree = ast.parse(content)
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.ClassDef):
                    sig = f"class {node.name}"
                    if node.bases:
                        base_names = []
                        for base in node.bases:
                            if isinstance(base, ast.Name):
                                base_names.append(base.id)
                            elif isinstance(base, ast.Attribute):
                                base_names.append(ast.unparse(base))
                        if base_names:
                            sig += f"({', '.join(base_names)})"
                    sig += ":"
                    
                    doc = ast.get_docstring(node)
                    if doc:
                        doc = doc.split('\n')[0].strip()[:50]
                    
                    symbols.append({'signature': sig, 'doc': doc or ''})
                    
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # Build function signature
                    sig = "async def " if isinstance(node, ast.AsyncFunctionDef) else "def "
                    sig += f"{node.name}("
                    
                    # Add parameters
                    args = []
                    for arg in node.args.args:
                        args.append(arg.arg)
                    if args:
                        sig += ", ".join(args)
                    sig += "):"
                    
                    doc = ast.get_docstring(node)
                    if doc:
                        doc = doc.split('\n')[0].strip()[:50]
                    
                    symbols.append({'signature': sig, 'doc': doc or ''})
        except:
            pass
        return symbols
    
    def _extract_regex_symbols_enhanced(self, content: str, language: str) -> List[Dict[str, str]]:
        """Extract symbols with signatures and comments for JS/TS/Go."""
        symbols = []
        
        # Language-specific patterns
        if language in ["javascript", "typescript"]:
            patterns = [
                # Function with preceding comment
                (r'(?://\s*(.+?)\n)?^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\((.*?)\)', 
                 lambda m: {'signature': f"function {m.group(2)}({m.group(3)}):", 'doc': (m.group(1) or '').strip()}),
                
                # Class with preceding comment
                (r'(?://\s*(.+?)\n)?^\s*(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?', 
                 lambda m: {'signature': f"class {m.group(2)}" + (f" extends {m.group(3)}" if m.group(3) else "") + ":", 
                           'doc': (m.group(1) or '').strip()}),
                
                # Arrow function with const
                (r'(?://\s*(.+?)\n)?^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\((.*?)\)\s*=>', 
                 lambda m: {'signature': f"const {m.group(2)} = ({m.group(3)}) =>", 'doc': (m.group(1) or '').strip()}),
            ]
        elif language == "go":
            patterns = [
                # Function with preceding comment
                (r'(?://\s*(.+?)\n)?^func\s+(\w+)\s*\((.*?)\)', 
                 lambda m: {'signature': f"func {m.group(2)}({m.group(3)})", 'doc': (m.group(1) or '').strip()}),
                
                # Method with preceding comment
                (r'(?://\s*(.+?)\n)?^func\s*\((\w+\s+[*]?\w+)\)\s*(\w+)\s*\((.*?)\)', 
                 lambda m: {'signature': f"func ({m.group(2)}) {m.group(3)}({m.group(4)})", 
                           'doc': (m.group(1) or '').strip()}),
                
                # Type struct with preceding comment
                (r'(?://\s*(.+?)\n)?^type\s+(\w+)\s+struct', 
                 lambda m: {'signature': f"type {m.group(2)} struct", 'doc': (m.group(1) or '').strip()}),
            ]
        else:
            return symbols
        
        # Apply patterns
        for pattern, extractor in patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                symbols.append(extractor(match))
        
        return symbols
    
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
    
    def what_breaks(self, exact_symbol: Dict[str, Any]) -> Dict[str, Any]:
        """
        Find what uses a symbol (reverse dependencies).
        Simplified to use basic text search for speed and simplicity.
        
        Returns a dictionary with references and a standard caveat.
        """
        symbol_name = exact_symbol['name']
        references = []
        
        # Use simple grep-like search for the symbol name
        # Check if ripgrep is available, otherwise fall back to Python
        try:
            # Try using ripgrep if available
            cmd = [
                "rg",
                "-w",  # whole word
                "--json",
                symbol_name,
                str(self.root_path)
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Parse ripgrep JSON output
                for line in result.stdout.strip().split('\n'):
                    if line:
                        try:
                            data = json.loads(line)
                            if data.get("type") == "match":
                                match_data = data.get("data", {})
                                references.append({
                                    "file": match_data.get("path", {}).get("text", ""),
                                    "line": match_data.get("line_number", 0),
                                    "text": match_data.get("lines", {}).get("text", "").strip()
                                })
                        except json.JSONDecodeError:
                            continue
            else:
                # Ripgrep not available or failed, fall back to Python
                references = self._python_text_search(symbol_name)
        except FileNotFoundError:
            # Ripgrep not installed, use Python fallback
            references = self._python_text_search(symbol_name)
        
        return {
            "references": references,
            "total_count": len(references),
            "note": f"Found {len(references)} potential references based on a text search for the name '{symbol_name}'. This may include comments, strings, or other unrelated symbols."
        }
    
    def _python_text_search(self, symbol_name: str) -> List[Dict[str, Any]]:
        """Fallback text search using Python when ripgrep is not available."""
        references = []
        gitignore_patterns = self._parse_gitignore()
        
        # Create word boundary pattern
        pattern = re.compile(r'\b' + re.escape(symbol_name) + r'\b')
        
        for file_path in self.root_path.rglob('*'):
            if not file_path.is_file():
                continue
            
            # Skip excluded files
            if self._should_exclude(file_path, gitignore_patterns):
                continue
            
            # Only search in source files
            if file_path.suffix.lower() not in LANGUAGE_MAP:
                continue
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        if pattern.search(line):
                            references.append({
                                "file": str(file_path),
                                "line": line_num,
                                "text": line.strip()
                            })
            except Exception:
                continue
        
        return references
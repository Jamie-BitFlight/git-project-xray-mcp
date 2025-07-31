"""Base parser interface and language detection for XRAY."""

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Set
import tree_sitter
from dataclasses import dataclass


@dataclass
class Symbol:
    """Represents a code symbol (function, class, method, etc.)."""
    name: str
    kind: str  # function, method, class, variable, import
    file: str
    line: int
    column: int = 0
    end_line: int = 0
    signature: Optional[str] = None
    parent_id: Optional[int] = None


@dataclass
class Edge:
    """Represents a dependency edge between symbols."""
    from_symbol: str  # Symbol name that depends on
    to_symbol: str    # Symbol name being depended on
    from_file: Optional[str] = None  # File context for from_symbol
    to_file: Optional[str] = None    # File context for to_symbol


class CanonicalIdGenerator:
    """Generates canonical IDs for symbols in a unified format."""
    
    @staticmethod
    def generate_canonical_id(symbol: Symbol, parent_symbol: Optional[Symbol] = None, repo_root: Path = None) -> str:
        """Generate canonical ID for a symbol.
        
        Args:
            symbol: The symbol to generate ID for
            parent_symbol: Parent symbol (for methods in classes)
            repo_root: Repository root path for relative file paths
            
        Returns:
            Canonical ID in format: file:Class.method or file:symbol
        """
        # Get relative file path
        if repo_root:
            file_path = str(Path(symbol.file).relative_to(repo_root))
        else:
            file_path = symbol.file
            
        # Build hierarchical name
        if parent_symbol:
            hierarchical_name = f"{parent_symbol.name}.{symbol.name}"
        else:
            hierarchical_name = symbol.name
            
        return f"{file_path}:{hierarchical_name}"
    
    @staticmethod
    def generate_all_aliases(symbol: Symbol, parent_symbol: Optional[Symbol] = None, 
                           repo_root: Path = None, context_file: str = None) -> List[dict]:
        """Generate all possible aliases for a symbol.
        
        Args:
            symbol: The symbol to generate aliases for
            parent_symbol: Parent symbol (for methods in classes)
            repo_root: Repository root path
            context_file: File where this symbol appears (for import context)
            
        Returns:
            List of alias dictionaries with keys: alias_type, alias_name, context_file
        """
        aliases = []
        
        # Canonical alias
        canonical_id = CanonicalIdGenerator.generate_canonical_id(symbol, parent_symbol, repo_root)
        aliases.append({
            "alias_type": "canonical",
            "alias_name": canonical_id,
            "context_file": None
        })
        
        # Simple name alias
        aliases.append({
            "alias_type": "simple", 
            "alias_name": symbol.name,
            "context_file": context_file
        })
        
        # Qualified name alias (for methods)
        if parent_symbol:
            qualified_name = f"{parent_symbol.name}.{symbol.name}"
            aliases.append({
                "alias_type": "qualified",
                "alias_name": qualified_name,
                "context_file": context_file
            })
        
        # Import alias (for imports in specific files)
        if symbol.kind == 'import' and context_file:
            aliases.append({
                "alias_type": "import",
                "alias_name": symbol.name,
                "context_file": context_file
            })
            
        return aliases


class LanguageParser(ABC):
    """Abstract base class for language-specific parsers."""
    
    def __init__(self, language: tree_sitter.Language):
        """Initialize parser with Tree-sitter language.
        
        Args:
            language: Tree-sitter language instance
        """
        self.language = language
        self.parser = tree_sitter.Parser(language)
    
    @abstractmethod
    def extract_symbols(self, source_code: bytes, file_path: str) -> List[Symbol]:
        """Extract symbols from source code.
        
        Args:
            source_code: Source code as bytes
            file_path: Path to the source file
            
        Returns:
            List of extracted symbols
        """
        pass
    
    @abstractmethod
    def extract_edges(self, source_code: bytes, file_path: str, symbols: List[Symbol]) -> List[Edge]:
        """Extract dependency edges from source code.
        
        Args:
            source_code: Source code as bytes
            file_path: Path to the source file
            symbols: List of symbols extracted from this file
            
        Returns:
            List of dependency edges
        """
        pass
    
    def parse_file(self, file_path: str) -> tuple[List[Symbol], List[Edge]]:
        """Parse a file and extract symbols and edges.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            Tuple of (symbols, edges)
        """
        try:
            with open(file_path, 'rb') as f:
                source_code = f.read()
            
            symbols = self.extract_symbols(source_code, file_path)
            edges = self.extract_edges(source_code, file_path, symbols)
            
            return symbols, edges
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
            return [], []


class LanguageDetector:
    """Detects programming language based on file extension."""
    
    # File extension to language mappings
    LANGUAGE_EXTENSIONS = {
        '.py': 'python',
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.go': 'go',
        '.rs': 'rust',
    }
    
    # Default ignore patterns
    DEFAULT_IGNORE_PATTERNS = {
        'node_modules', '.git', '__pycache__', '.pytest_cache',
        'dist', 'build', '.venv', 'venv', '.env',
        '.mypy_cache', '.tox', 'coverage', '.nyc_output',
        'vendor', 'target'  # Go and Rust build directories
    }
    
    @classmethod
    def detect_language(cls, file_path: str) -> Optional[str]:
        """Detect language from file extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Language name if detected, None otherwise
        """
        ext = Path(file_path).suffix.lower()
        return cls.LANGUAGE_EXTENSIONS.get(ext)
    
    @classmethod
    def is_supported_file(cls, file_path: str) -> bool:
        """Check if file is supported for parsing.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file is supported, False otherwise
        """
        return cls.detect_language(file_path) is not None
    
    @classmethod
    def should_ignore_path(cls, path: str, ignore_patterns: Optional[Set[str]] = None) -> bool:
        """Check if path should be ignored during indexing.
        
        Args:
            path: Path to check
            ignore_patterns: Additional ignore patterns (optional)
            
        Returns:
            True if path should be ignored, False otherwise
        """
        path_obj = Path(path)
        
        # Use default patterns if none provided
        if ignore_patterns is None:
            ignore_patterns = cls.DEFAULT_IGNORE_PATTERNS
        else:
            ignore_patterns = ignore_patterns.union(cls.DEFAULT_IGNORE_PATTERNS)
        
        # Check each path component
        for part in path_obj.parts:
            if part in ignore_patterns:
                print(f"Ignoring path: {path}", file=sys.stderr)
                return True
        
        # Check if any parent directory should be ignored
        for pattern in ignore_patterns:
            if pattern in str(path_obj):
                return True
        
        return False
    
    @classmethod
    def find_source_files(cls, root_path: str, ignore_patterns: Optional[Set[str]] = None) -> List[str]:
        """Find all supported source files in a directory tree.
        
        Args:
            root_path: Root directory to search
            ignore_patterns: Additional ignore patterns (optional)
            
        Returns:
            List of source file paths
        """
        source_files = []
        root = Path(root_path).resolve()
        
        for file_path in root.rglob('*'):
            print(f"Found file: {file_path}", file=sys.stderr)
            if not file_path.is_file():
                continue
            
            # Convert to string for processing
            file_str = str(file_path)
            
            # Skip ignored paths
            if cls.should_ignore_path(file_str, ignore_patterns):
                continue
            
            # Check if file is supported
            if cls.is_supported_file(file_str):
                source_files.append(file_str)
        
        return sorted(source_files)


class LanguageRegistry:
    """Registry for managing language parsers."""
    
    def __init__(self):
        """Initialize the language registry."""
        self._parsers: Dict[str, LanguageParser] = {}
        self._languages: Dict[str, tree_sitter.Language] = {}
    
    def register_language(self, name: str, language: tree_sitter.Language, parser_class: type):
        """Register a language with its parser.
        
        Args:
            name: Language name
            language: Tree-sitter language instance
            parser_class: Parser class for this language
        """
        self._languages[name] = language
        self._parsers[name] = parser_class(language)
    
    def get_parser(self, language: str) -> Optional[LanguageParser]:
        """Get parser for a language.
        
        Args:
            language: Language name
            
        Returns:
            Parser instance if available, None otherwise
        """
        return self._parsers.get(language)
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages.
        
        Returns:
            List of supported language names
        """
        return list(self._parsers.keys())
    
    def parse_file(self, file_path: str) -> tuple[List[Symbol], List[Edge]]:
        """Parse a file using the appropriate language parser.
        
        Args:
            file_path: Path to the file to parse
            
        Returns:
            Tuple of (symbols, edges)
        """
        language = LanguageDetector.detect_language(file_path)
        if not language:
            return [], []
        
        parser = self.get_parser(language)
        if not parser:
            return [], []
        
        return parser.parse_file(file_path)


def load_tree_sitter_languages() -> Dict[str, tree_sitter.Language]:
    """Load Tree-sitter languages.
    
    Returns:
        Dictionary mapping language names to Language instances
    """
    languages = {}
    
    try:
        import tree_sitter_python
        languages['python'] = tree_sitter.Language(tree_sitter_python.language())
    except ImportError:
        print("Warning: tree-sitter-python not available")
    
    try:
        import tree_sitter_javascript
        languages['javascript'] = tree_sitter.Language(tree_sitter_javascript.language())
    except ImportError:
        print("Warning: tree-sitter-javascript not available")
    
    try:
        import tree_sitter_typescript
        languages['typescript'] = tree_sitter.Language(tree_sitter_typescript.language_typescript())
    except ImportError:
        print("Warning: tree-sitter-typescript not available")
    
    try:
        import tree_sitter_go
        languages['go'] = tree_sitter.Language(tree_sitter_go.language())
    except ImportError:
        print("Warning: tree-sitter-go not available")
    
    return languages
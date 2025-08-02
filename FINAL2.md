# XRAY: Pure Python Implementation Plan

## 1. Philosophy: Zero-Dependency Code Intelligence

The original XRAY philosophy remains: provide LLMs with structural context that's better than grep but simpler than LSP. This revision prioritizes **ease of installation** above perfect accuracy.

### Core Principles:
- **Zero external binaries** - Pure Python implementation
- **Single command install** - Just `pip install -e .`
- **High recall over high precision** - Cast a wide net, let the LLM filter
- **Progressive enhancement** - Pluggable architecture for future improvements

### Key Insight:
LLMs are intelligent enough to filter out false positives. Therefore, we optimize for finding ALL potential symbols (high recall) rather than being overly precise. This makes our regex patterns simpler and more maintainable.

## 2. Architecture: Hybrid Parsing Approach

### Language-Specific Strategies:
- **Python**: Use built-in `ast` module (100% accurate, zero deps)
- **JavaScript/TypeScript**: Regex-based patterns for common constructs
- **Go**: Regex-based patterns for common constructs

### Why This Works:
1. XRAY doesn't need to parse entire programs - just find definitions and calls
2. We can be conservative with regex - prefer false negatives over false positives
3. The LLM can handle some imprecision if the tool is useful overall

## 3. Tool Specifications

### build_index(root_path)
**Purpose**: Generate a visual file tree of the repository

**Implementation**:
- Pure Python directory walking
- Respect .gitignore rules (using simple pattern matching)
- Apply default exclusions
- Return formatted tree string

**No parsing required** - This is just file system traversal.

### find_symbol(root_path, query)
**Purpose**: Locate symbol definitions using fuzzy search

**Implementation**:
1. For each supported file:
   - Python files: Parse with `ast` module
   - JS/TS/Go files: Apply regex patterns for definitions
2. Collect all symbol names and locations
3. Use `thefuzz` library for fuzzy matching against query
4. Return top 5-10 matches as structured objects

**Output Format**:
```json
{
  "name": "authenticate_user",
  "type": "function",
  "path": "/absolute/path/to/file.py",
  "start_line": 55,
  "end_line": 72
}
```

### what_depends(exact_symbol)
**Purpose**: Find what a symbol uses (calls, imports)

**Implementation**:
1. Read the file content for the given symbol's location
2. Extract the code block between start_line and end_line
3. Apply language-specific patterns to find:
   - Function calls
   - Method calls
   - Import statements
4. Return list of dependency names

### what_breaks(exact_symbol)
**Purpose**: Find what uses a symbol (reverse dependencies)

**Implementation**:
1. Search all files in the repository
2. Look for calls to the symbol's name
3. Return locations with the standard caveat about name-based matching

## 4. Parser Architecture

### Base Parser Interface:
```python
class BaseParser:
    def find_definitions(self, content: str) -> List[Symbol]:
        """Find all symbol definitions in the content"""
        raise NotImplementedError
    
    def find_calls(self, content: str) -> List[str]:
        """Find all function/method calls in the content"""
        raise NotImplementedError
    
    def find_imports(self, content: str) -> List[str]:
        """Find all imports in the content"""
        raise NotImplementedError
```

### Language Implementations:
- `PythonASTParser`: Uses `ast` module
- `RegexParser`: Base class for regex-based parsing
- `JavaScriptRegexParser`: JS-specific patterns
- `TypeScriptRegexParser`: TS-specific patterns (extends JS)
- `GoRegexParser`: Go-specific patterns

## 5. Regex Design Principles

### Safety Rules:
1. **Line-start anchoring**: Use `^` to avoid matching in strings/comments
2. **Word boundaries**: Use `\b` to avoid partial matches
3. **Multiline mode**: Use `re.MULTILINE` for proper `^` behavior
4. **Conservative matching**: Prefer missing edge cases over false positives

### Pattern Categories:
1. **Simple patterns**: For unambiguous constructs (e.g., `func name()` in Go)
2. **Context-aware patterns**: Check indentation for nested definitions
3. **Negative lookbehind**: Avoid commented-out code

## 6. Implementation Timeline

1. Create base parser architecture
2. Implement Python AST parser
3. Design and test regex patterns for each language
4. Implement core tools (build_index, find_symbol, etc.)
5. Add fuzzy matching with thefuzz
6. Test on real codebases
7. Document limitations clearly

## 7. Future Enhancements

The architecture allows for optional improvements:
- Users can install `pyjsparser` for better JS parsing
- Semgrep can be used as a backend if available
- Tree-sitter can be plugged in if desired

But the key is: **the tool works immediately after installation with no external dependencies**.

## 8. Regex Patterns

### JavaScript/TypeScript Patterns

**Symbol Definitions:**
```python
# Function declarations
r'(?:^|\n)\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)'

# Arrow functions and function expressions  
r'(?:^|\n)\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:function|\()'

# Classes
r'(?:^|\n)\s*(?:export\s+)?(?:default\s+)?class\s+(\w+)'

# Class methods (when inside class context)
r'(?:^|\n)\s+(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{'
```

**Function Calls:**
```python
# Function/method calls
r'\b(\w+)\s*\('  # Matches: func(, obj.method(, array.map(

# Import statements
r'import\s+.*?from\s+[\'"]([^\'"]]+)'
r'require\s*\(\s*[\'"]([^\'"]]+)'
```

### Go Patterns

**Symbol Definitions:**
```python
# Functions and methods
r'(?:^|\n)func\s+(?:\([^)]+\)\s+)?(\w+)\s*\('

# Types
r'(?:^|\n)type\s+(\w+)\s+(?:struct|interface)'
```

**Function Calls:**
```python
# Function calls
r'\b(\w+)\s*\('

# Package imports
r'import\s+"([^"]+)"'
```

## 9. Limitations and Transparency

The tool will clearly document its behavior:
- "Results may include symbols from comments, strings, and other contexts"
- "The LLM should filter results based on surrounding context"
- "This tool optimizes for finding all potential matches (high recall) over accuracy"

Example tool description:
```
find_symbol: Searches for symbol definitions using pattern matching. 
Results may include false positives from comments or strings - the LLM 
should evaluate context to determine relevance. This approach ensures 
no important symbols are missed.
```

The goal is to be useful, not perfect. By casting a wide net and providing context, we enable LLMs to make intelligent decisions about the results.
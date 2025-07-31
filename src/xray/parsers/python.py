"""Python parser using Tree-sitter for XRAY."""

import tree_sitter
from typing import List, Set
from .base import LanguageParser, Symbol, Edge


class PythonParser(LanguageParser):
    """Parser for Python source code."""
    
    def __init__(self, language: tree_sitter.Language):
        """Initialize Python parser."""
        super().__init__(language)
        
        # Simplified Tree-sitter queries for core Python symbols
        self.symbol_query = tree_sitter.Query(self.language, """
            (function_definition name: (identifier) @function.name) @function.def
            (class_definition name: (identifier) @class.name) @class.def
            (import_statement (dotted_name) @import.name)
            (import_from_statement (dotted_name) @import.module)
        """)
        
        # Simple call query for impact analysis
        self.call_query = tree_sitter.Query(self.language, """
            (call function: (identifier) @call.name)
            (call function: (attribute attribute: (identifier) @call.method))
        """)
    
    def extract_symbols(self, source_code: bytes, file_path: str) -> List[Symbol]:
        """Extract core symbols from Python source code."""
        tree = self.parser.parse(source_code)
        symbols = []
        
        # Extract all symbols in one pass
        matches = self.symbol_query.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            # Functions
            if 'function.name' in captures:
                name_node = captures['function.name'][0]
                def_node = captures['function.def'][0]
                symbols.append(Symbol(
                    name=name_node.text.decode('utf-8'),
                    kind='function',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    end_line=def_node.end_point[0] + 1,
                    signature=f"def {name_node.text.decode('utf-8')}()"
                ))
            
            # Classes  
            elif 'class.name' in captures:
                name_node = captures['class.name'][0]
                def_node = captures['class.def'][0]
                symbols.append(Symbol(
                    name=name_node.text.decode('utf-8'),
                    kind='class',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    end_line=def_node.end_point[0] + 1,
                    signature=f"class {name_node.text.decode('utf-8')}"
                ))
                
            # Imports
            elif 'import.name' in captures:
                name_node = captures['import.name'][0]
                symbols.append(Symbol(
                    name=name_node.text.decode('utf-8'),
                    kind='import',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    signature=f"import {name_node.text.decode('utf-8')}"
                ))
                
            elif 'import.module' in captures:
                name_node = captures['import.module'][0]
                symbols.append(Symbol(
                    name=name_node.text.decode('utf-8'),
                    kind='import',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    signature=f"from {name_node.text.decode('utf-8')} import"
                ))
        
        return symbols
    
    def extract_edges(self, source_code: bytes, file_path: str, symbols: List[Symbol]) -> List[Edge]:
        """Extract dependency edges for impact analysis."""
        tree = self.parser.parse(source_code)
        edges = []
        symbol_names = {symbol.name for symbol in symbols}
        
        # Extract function calls for impact analysis
        matches = self.call_query.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            caller = self._find_enclosing_function_name(tree.root_node, match[0])
            
            if caller and 'call.name' in captures:
                called_function = captures['call.name'][0].text.decode('utf-8')
                if called_function and called_function not in {'print', 'len', 'str', 'int'}:
                    edges.append(Edge(
                        from_symbol=caller,
                        to_symbol=called_function,
                        from_file=file_path,
                        to_file=None
                    ))
                    
            elif caller and 'call.method' in captures:
                method_name = captures['call.method'][0].text.decode('utf-8')
                if method_name:
                    edges.append(Edge(
                        from_symbol=caller,
                        to_symbol=method_name,
                        from_file=file_path,
                        to_file=None
                    ))
        
        return edges
    
    def _find_enclosing_function_name(self, root_node: tree_sitter.Node, node: tree_sitter.Node) -> str:
        """Find the function containing this node for impact analysis."""
        current = node.parent
        while current:
            if current.type == 'function_definition':
                for child in current.children:
                    if child.type == 'identifier':
                        return child.text.decode('utf-8')
            current = current.parent
        return None
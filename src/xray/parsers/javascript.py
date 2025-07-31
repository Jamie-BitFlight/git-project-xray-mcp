"""JavaScript parser using Tree-sitter for XRAY."""

import tree_sitter
from typing import List, Set
from .base import LanguageParser, Symbol, Edge


class JavaScriptParser(LanguageParser):
    """Parser for JavaScript source code."""
    
    def __init__(self, language: tree_sitter.Language):
        """Initialize JavaScript parser."""
        super().__init__(language)
        
        # Simplified Tree-sitter queries for core JavaScript symbols
        self.symbol_query = tree_sitter.Query(self.language, """
            (function_declaration name: (identifier) @function.name) @function.def
            (class_declaration name: (identifier) @class.name) @class.def
            (variable_declarator name: (identifier) @var.name value: (arrow_function)) @arrow.def
            (variable_declarator name: (identifier) @var.name value: (function_expression)) @func.def
            (import_statement source: (string (string_fragment) @import.source))
            (export_statement declaration: (function_declaration name: (identifier) @export.function))
            (export_statement declaration: (class_declaration name: (identifier) @export.class))
        """)
        
        # Simple call query for impact analysis
        self.call_query = tree_sitter.Query(self.language, """
            (call_expression function: (identifier) @call.name)
            (call_expression function: (member_expression property: (property_identifier) @call.method))
        """)
    
    def extract_symbols(self, source_code: bytes, file_path: str) -> List[Symbol]:
        """Extract core symbols from JavaScript source code."""
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
                    signature=f"function {name_node.text.decode('utf-8')}()"
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
                
            # Arrow functions
            elif 'var.name' in captures and 'arrow.def' in captures:
                name_node = captures['var.name'][0]
                def_node = captures['arrow.def'][0]
                symbols.append(Symbol(
                    name=name_node.text.decode('utf-8'),
                    kind='function',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    end_line=def_node.end_point[0] + 1,
                    signature=f"const {name_node.text.decode('utf-8')} = () => {{}}"
                ))
                
            # Function expressions
            elif 'var.name' in captures and 'func.def' in captures:
                name_node = captures['var.name'][0]
                def_node = captures['func.def'][0]
                symbols.append(Symbol(
                    name=name_node.text.decode('utf-8'),
                    kind='function',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    end_line=def_node.end_point[0] + 1,
                    signature=f"const {name_node.text.decode('utf-8')} = function() {{}}"
                ))
                
            # Imports
            elif 'import.source' in captures:
                source_node = captures['import.source'][0]
                source_text = source_node.text.decode('utf-8')
                symbols.append(Symbol(
                    name=source_text.split('/')[-1].replace('.js', ''),
                    kind='import',
                    file=file_path,
                    line=source_node.start_point[0] + 1,
                    column=source_node.start_point[1],
                    signature=f"import from '{source_text}'"
                ))
                
            # Exports
            elif 'export.function' in captures:
                name_node = captures['export.function'][0]
                symbols.append(Symbol(
                    name=name_node.text.decode('utf-8'),
                    kind='export',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    signature=f"export function {name_node.text.decode('utf-8')}()"
                ))
                
            elif 'export.class' in captures:
                name_node = captures['export.class'][0]
                symbols.append(Symbol(
                    name=name_node.text.decode('utf-8'),
                    kind='export',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    signature=f"export class {name_node.text.decode('utf-8')}"
                ))
        
        return symbols
    
    def extract_edges(self, source_code: bytes, file_path: str, symbols: List[Symbol]) -> List[Edge]:
        """Extract dependency edges for impact analysis."""
        tree = self.parser.parse(source_code)
        edges = []
        
        # Extract function calls for impact analysis
        matches = self.call_query.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            caller = self._find_enclosing_function_name(tree.root_node, match[0])
            
            if caller and 'call.name' in captures:
                called_function = captures['call.name'][0].text.decode('utf-8')
                if called_function and called_function not in {'console', 'require', 'module'}:
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
            if current.type in ['function_declaration', 'function_expression']:
                for child in current.children:
                    if child.type == 'identifier':
                        return child.text.decode('utf-8')
            elif current.type == 'variable_declarator':
                # Arrow function or function expression assigned to variable
                for child in current.children:
                    if child.type == 'identifier':
                        return child.text.decode('utf-8')
            current = current.parent
        return None
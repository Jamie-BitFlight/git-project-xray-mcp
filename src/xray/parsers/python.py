"""Python parser using Tree-sitter for XRAY-Lite."""

import tree_sitter
from typing import List, Set
from .base import LanguageParser, Symbol, Edge


class PythonParser(LanguageParser):
    """Parser for Python source code."""
    
    def __init__(self, language: tree_sitter.Language):
        """Initialize Python parser."""
        super().__init__(language)
        
        # Tree-sitter queries for Python symbols
        self.function_query = tree_sitter.Query(self.language, """
            (function_definition 
                name: (identifier) @function.name
            ) @function.def
        """)
        
        self.class_query = tree_sitter.Query(self.language, """
            (class_definition 
                name: (identifier) @class.name
            ) @class.def
        """)
        
        # Simplified import query to focus on basic patterns that work
        self.import_query = tree_sitter.Query(self.language, """
            (import_statement 
                name: (dotted_name) @import.name
            ) @import.stmt
            
            (import_from_statement 
                name: (dotted_name) @import.name
            ) @import.from
        """)
        
        # Enhanced call query to capture different types of calls
        self.call_query = tree_sitter.Query(self.language, """
            (call 
                function: (identifier) @call.name
            ) @call.expr
            
            (call 
                function: (attribute
                    object: (identifier) @call.object
                    attribute: (identifier) @call.method
                )
            ) @call.method_expr
            
            (call 
                function: (attribute
                    object: (call) @call.chained_object
                    attribute: (identifier) @call.chained_method
                )
            ) @call.chained_expr
        """)
        
        # Query for attribute access (non-call)
        self.attribute_query = tree_sitter.Query(self.language, """
            (attribute
                object: (identifier) @attr.object
                attribute: (identifier) @attr.name
            ) @attr.expr
        """)
        
        # Enhanced assignment query to track function calls and class instantiation
        self.assignment_query = tree_sitter.Query(self.language, """
            (assignment
                left: (identifier) @assign.var
                right: (call
                    function: (identifier) @assign.function
                ) @assign.call
            ) @assign.expr
            
            (assignment
                left: (identifier) @assign.var
                right: (call
                    function: (attribute
                        object: (identifier) @assign.object
                        attribute: (identifier) @assign.method
                    )
                ) @assign.method_call
            ) @assign.method_expr
        """)
        
        # Query for argument references (class names passed as arguments)
        self.argument_query = tree_sitter.Query(self.language, """
            (argument_list
                (identifier) @arg.name
            ) @arg.list
        """)
    
    def extract_symbols(self, source_code: bytes, file_path: str) -> List[Symbol]:
        """Extract symbols from Python source code."""
        tree = self.parser.parse(source_code)
        symbols = []
        
        # Extract functions using correct Tree-sitter API
        query_cursor = tree_sitter.QueryCursor(self.function_query)
        matches = query_cursor.matches(tree.root_node)
        for match in matches:
            captures = match[1]  # match[1] is already the captures dict
            if 'function.name' in captures:
                name_node = captures['function.name'][0]  # First node in the capture list
                def_node = captures['function.def'][0]
                
                # Get function signature
                signature = self._extract_function_signature(def_node, source_code)
                
                symbol = Symbol(
                    name=name_node.text.decode('utf-8'),
                    kind='function',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    end_line=def_node.end_point[0] + 1,
                    signature=signature
                )
                symbols.append(symbol)
        
        # Extract classes
        class_symbols = {}  # Track class symbols for method parent assignment
        query_cursor = tree_sitter.QueryCursor(self.class_query)
        matches = query_cursor.matches(tree.root_node)
        for match in matches:
            captures = match[1]  # match[1] is already the captures dict
            if 'class.name' in captures:
                name_node = captures['class.name'][0]  # First node in the capture list
                def_node = captures['class.def'][0]
                
                symbol = Symbol(
                    name=name_node.text.decode('utf-8'),
                    kind='class',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    end_line=def_node.end_point[0] + 1,
                    signature=f"class {name_node.text.decode('utf-8')}"
                )
                symbols.append(symbol)
                class_symbols[name_node.text.decode('utf-8')] = len(symbols) - 1
        
        # Extract methods (functions inside classes)
        # We'll detect methods by finding functions that are children of classes
        for symbol in symbols:
            if symbol.kind == 'function':
                # Check if this function is inside a class
                parent_class = self._find_parent_class_for_function(tree.root_node, symbol.line - 1)
                if parent_class:
                    parent_class_name = parent_class.text.decode('utf-8')
                    if parent_class_name in class_symbols:
                        symbol.kind = 'method'
                        symbol.parent_id = class_symbols[parent_class_name]
        
        # Extract imports with simplified logic
        query_cursor = tree_sitter.QueryCursor(self.import_query)
        matches = query_cursor.matches(tree.root_node)
        for match in matches:
            captures = match[1]  # match[1] is already the captures dict
            
            # Handle different import patterns
            if 'import.name' in captures:
                # Simple import or from X import Y
                name_node = captures['import.name'][0]
                import_name = name_node.text.decode('utf-8')
                signature = f"import {import_name}"  # Simplified for now
                
                symbol = Symbol(
                    name=import_name,
                    kind='import',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    signature=signature
                )
                symbols.append(symbol)
                
        
        return symbols
    
    def extract_edges(self, source_code: bytes, file_path: str, symbols: List[Symbol]) -> List[Edge]:
        """Extract dependency edges from Python source code."""
        tree = self.parser.parse(source_code)
        edges = []
        
        # Create symbol lookup for this file (for local validation)
        symbol_names = {symbol.name for symbol in symbols}
        
        # Helper function to check if a symbol exists globally
        def symbol_exists_globally(name: str) -> bool:
            # For now, assume all non-empty names could be valid symbols
            # The actual resolution will happen in the indexer using the alias system
            return bool(name and name != "<module>")
        
        # Extract function calls (simple and method calls)
        query_cursor = tree_sitter.QueryCursor(self.call_query)
        matches = query_cursor.matches(tree.root_node)
        for match in matches:
            captures = match[1]  # match[1] is already the captures dict
            caller = None
            called_function = None
            
            if 'call.name' in captures:
                # Simple function call like: func()
                call_node = captures['call.name'][0]
                called_function = call_node.text.decode('utf-8')
                caller = self._find_enclosing_function(call_node)
                
            elif 'call.method' in captures and 'call.object' in captures:
                # Method call like: obj.method() or self.method()
                method_node = captures['call.method'][0]
                object_node = captures['call.object'][0]
                called_function = method_node.text.decode('utf-8')
                object_name = object_node.text.decode('utf-8')
                caller = self._find_enclosing_function(method_node)
                
                if caller:
                    # Handle self.method() calls specially
                    if object_name == 'self':
                        # For self.method(), create edge to the method within same class
                        if symbol_exists_globally(called_function):
                            edges.append(Edge(
                                from_symbol=caller,
                                to_symbol=called_function,
                                from_file=file_path,
                                to_file=file_path
                            ))
                    else:
                        # For any method call, try to create edge to the method name
                        # This handles cases like: indexer.build_index() where indexer is a local var
                        # Use None for to_file to enable cross-file resolution in indexer
                        if symbol_exists_globally(called_function):
                            edges.append(Edge(
                                from_symbol=caller,
                                to_symbol=called_function,
                                from_file=file_path,
                                to_file=None  # Enable cross-file resolution
                            ))
                        
                        # Also create edge to the object if it's a known symbol
                        if symbol_exists_globally(object_name):
                            edges.append(Edge(
                                from_symbol=caller,
                                to_symbol=object_name,
                                from_file=file_path,
                                to_file=file_path
                            ))
                    
            elif 'call.chained_method' in captures:
                # Chained method call like: obj.method().another()
                method_node = captures['call.chained_method'][0]
                called_function = method_node.text.decode('utf-8')
                caller = self._find_enclosing_function(method_node)
            
            # Create edge if we found a valid call (use global symbol check)
            if caller and called_function and symbol_exists_globally(called_function):
                edges.append(Edge(
                    from_symbol=caller,
                    to_symbol=called_function,
                    from_file=file_path,
                    to_file=None  # Enable cross-file resolution
                ))
        
        # Extract attribute access (non-call dependencies)
        query_cursor = tree_sitter.QueryCursor(self.attribute_query)
        matches = query_cursor.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            if 'attr.object' in captures and 'attr.name' in captures:
                object_node = captures['attr.object'][0]
                attr_node = captures['attr.name'][0]
                object_name = object_node.text.decode('utf-8')
                attr_name = attr_node.text.decode('utf-8')
                
                caller = self._find_enclosing_function(object_node)
                
                # Create edges for both object and attribute access
                if caller:
                    if symbol_exists_globally(object_name):
                        edges.append(Edge(
                            from_symbol=caller,
                            to_symbol=object_name,
                            from_file=file_path,
                            to_file=file_path
                        ))
                    if symbol_exists_globally(attr_name):
                        edges.append(Edge(
                            from_symbol=caller,
                            to_symbol=attr_name,
                            from_file=file_path,
                            to_file=None  # Enable cross-file resolution
                        ))
        
        # Extract assignment dependencies (function calls and instantiation)
        query_cursor = tree_sitter.QueryCursor(self.assignment_query)
        matches = query_cursor.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            if 'assign.function' in captures:
                # Assignment like: indexer = get_indexer()
                function_node = captures['assign.function'][0]
                function_name = function_node.text.decode('utf-8')
                
                caller = self._find_enclosing_function(function_node)
                if caller and symbol_exists_globally(function_name):
                    edges.append(Edge(
                        from_symbol=caller,
                        to_symbol=function_name,
                        from_file=file_path,
                        to_file=None  # Enable cross-file resolution
                    ))
                    
            elif 'assign.method' in captures and 'assign.object' in captures:
                # Assignment like: result = obj.method()
                method_node = captures['assign.method'][0]
                object_node = captures['assign.object'][0]
                method_name = method_node.text.decode('utf-8')
                object_name = object_node.text.decode('utf-8')
                
                caller = self._find_enclosing_function(method_node)
                if caller:
                    # Create edge to the method
                    if symbol_exists_globally(method_name):
                        edges.append(Edge(
                            from_symbol=caller,
                            to_symbol=method_name,
                            from_file=file_path,
                            to_file=None  # Enable cross-file resolution
                        ))
                    # Create edge to the object  
                    if symbol_exists_globally(object_name):
                        edges.append(Edge(
                            from_symbol=caller,
                            to_symbol=object_name,
                            from_file=file_path,
                            to_file=file_path
                        ))
        
        # Extract argument references (class names as function arguments)
        query_cursor = tree_sitter.QueryCursor(self.argument_query)
        matches = query_cursor.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            if 'arg.name' in captures:
                arg_node = captures['arg.name'][0]
                arg_name = arg_node.text.decode('utf-8')
                
                caller = self._find_enclosing_function(arg_node)
                if caller and symbol_exists_globally(arg_name):
                    edges.append(Edge(
                        from_symbol=caller,
                        to_symbol=arg_name,
                        from_file=file_path,
                        to_file=None  # Enable cross-file resolution
                    ))
        
        return edges
    
    def _extract_function_signature(self, func_node: tree_sitter.Node, source_code: bytes) -> str:
        """Extract function signature from function definition node."""
        try:
            # Find the function definition line
            start_byte = func_node.start_byte
            end_byte = func_node.start_byte
            
            # Find the end of the function header (before the colon)
            while end_byte < len(source_code) and source_code[end_byte:end_byte+1] != b':':
                end_byte += 1
            
            signature_bytes = source_code[start_byte:end_byte]
            return signature_bytes.decode('utf-8', errors='ignore').strip()
        except:
            return ""
    
    def _find_parent_class_for_function(self, root_node: tree_sitter.Node, func_line: int) -> tree_sitter.Node:
        """Find the parent class of a function at a specific line."""
        def traverse(node):
            if node.type == 'class_definition':
                class_start = node.start_point[0]
                class_end = node.end_point[0]
                if class_start < func_line < class_end:
                    # Find the class name identifier
                    for child in node.children:
                        if child.type == 'identifier':
                            return child
            
            for child in node.children:
                result = traverse(child)
                if result:
                    return result
            return None
        
        return traverse(root_node)
    
    def _find_enclosing_function(self, node: tree_sitter.Node) -> str:
        """Find the name of the function/method that encloses this node."""
        current = node.parent
        class_name = None
        
        while current:
            if current.type == 'function_definition':
                # Find the function name
                for child in current.children:
                    if child.type == 'identifier':
                        func_name = child.text.decode('utf-8')
                        
                        # If we found a class, prefix the method name
                        if class_name:
                            return f"{class_name}.{func_name}"
                        return func_name
                break
            elif current.type == 'class_definition' and not class_name:
                # Remember the class name for method qualification
                for child in current.children:
                    if child.type == 'identifier':
                        class_name = child.text.decode('utf-8')
                        break
            current = current.parent
        
        # If no enclosing function found, return module-level indicator
        return "<module>" if class_name is None else None
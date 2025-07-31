"""JavaScript parser using Tree-sitter for XRAY."""

import tree_sitter
from typing import List, Set
from .base import LanguageParser, Symbol, Edge


class JavaScriptParser(LanguageParser):
    """Parser for JavaScript source code."""
    
    def __init__(self, language: tree_sitter.Language):
        """Initialize JavaScript parser."""
        super().__init__(language)
        
        # Tree-sitter queries for JavaScript symbols
        self.function_query = tree_sitter.Query(self.language, """
            (function_declaration 
                name: (identifier) @function.name
            ) @function.def
            
            (function_expression
                name: (identifier) @function.name
            ) @function.expr
            
            (arrow_function
                parameter: (identifier) @arrow.param
            ) @arrow.func
            
            (variable_declarator
                name: (identifier) @var.name
                value: (arrow_function) @var.arrow
            ) @var.arrow_decl
            
            (variable_declarator
                name: (identifier) @var.name
                value: (function_expression) @var.func
            ) @var.func_decl
        """)
        
        self.class_query = tree_sitter.Query(self.language, """
            (class_declaration 
                name: (identifier) @class.name
            ) @class.def
            
            (class_expression
                name: (identifier) @class.name
            ) @class.expr
        """)
        
        # Method definitions inside classes
        self.method_query = tree_sitter.Query(self.language, """
            (method_definition
                name: (property_identifier) @method.name
            ) @method.def
            
            (method_definition
                name: (private_property_identifier) @method.name
            ) @method.private
        """)
        
        # Import/export queries
        self.import_query = tree_sitter.Query(self.language, """
            (import_statement
                source: (string (string_fragment) @import.source)
            ) @import.stmt
            
            (import_clause
                (identifier) @import.default
            ) @import.default_clause
            
            (import_clause
                (named_imports
                    (import_specifier
                        name: (identifier) @import.name
                    )
                )
            ) @import.named
            
            (namespace_import
                (identifier) @import.namespace
            ) @import.namespace_stmt
        """)
        
        self.export_query = tree_sitter.Query(self.language, """
            (export_statement
                declaration: (function_declaration
                    name: (identifier) @export.function
                )
            ) @export.func_stmt
            
            (export_statement
                declaration: (class_declaration
                    name: (identifier) @export.class
                )
            ) @export.class_stmt
            
            (export_statement
                declaration: (variable_declaration
                    (variable_declarator
                        name: (identifier) @export.var
                    )
                )
            ) @export.var_stmt
            
            (export_default_declaration
                declaration: (identifier) @export.default
            ) @export.default_stmt
            
            (export_specifier
                name: (identifier) @export.name
            ) @export.spec
        """)
        
        # Call expressions
        self.call_query = tree_sitter.Query(self.language, """
            (call_expression
                function: (identifier) @call.name
            ) @call.expr
            
            (call_expression
                function: (member_expression
                    object: (identifier) @call.object
                    property: (property_identifier) @call.method
                )
            ) @call.method_expr
            
            (new_expression
                constructor: (identifier) @new.class
            ) @new.expr
        """)
        
        # Member expression (property access)
        self.member_query = tree_sitter.Query(self.language, """
            (member_expression
                object: (identifier) @member.object
                property: (property_identifier) @member.property
            ) @member.expr
        """)
        
        # Variable assignments that might be dependencies
        self.assignment_query = tree_sitter.Query(self.language, """
            (variable_declarator
                name: (identifier) @assign.var
                value: (call_expression
                    function: (identifier) @assign.function
                )
            ) @assign.call
            
            (variable_declarator
                name: (identifier) @assign.var
                value: (new_expression
                    constructor: (identifier) @assign.class
                )
            ) @assign.new
            
            (assignment_expression
                left: (identifier) @assign.target
                right: (call_expression
                    function: (identifier) @assign.func
                )
            ) @assign.expr
        """)
    
    def extract_symbols(self, source_code: bytes, file_path: str) -> List[Symbol]:
        """Extract symbols from JavaScript source code."""
        tree = self.parser.parse(source_code)
        symbols = []
        
        # Extract functions
        matches = self.function_query.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            # Handle function declarations
            if 'function.name' in captures and 'function.def' in captures:
                name_node = captures['function.name'][0]
                def_node = captures['function.def'][0]
                
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
            
            # Handle arrow functions assigned to variables
            elif 'var.name' in captures and 'var.arrow' in captures:
                name_node = captures['var.name'][0]
                arrow_node = captures['var.arrow'][0]
                
                signature = f"const {name_node.text.decode('utf-8')} = () => {{}}"
                
                symbol = Symbol(
                    name=name_node.text.decode('utf-8'),
                    kind='function',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    end_line=arrow_node.end_point[0] + 1,
                    signature=signature
                )
                symbols.append(symbol)
            
            # Handle function expressions assigned to variables
            elif 'var.name' in captures and 'var.func' in captures:
                name_node = captures['var.name'][0]
                func_node = captures['var.func'][0]
                
                signature = f"const {name_node.text.decode('utf-8')} = function() {{}}"
                
                symbol = Symbol(
                    name=name_node.text.decode('utf-8'),
                    kind='function',
                    file=file_path,
                    line=name_node.start_point[0] + 1,
                    column=name_node.start_point[1],
                    end_line=func_node.end_point[0] + 1,
                    signature=signature
                )
                symbols.append(symbol)
        
        # Extract classes
        class_symbols = {}  # Track class symbols for method parent assignment
        matches = self.class_query.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            if 'class.name' in captures:
                name_node = captures['class.name'][0]
                def_node = captures.get('class.def', captures.get('class.expr', [None]))[0]
                
                if def_node:
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
        
        # Extract methods
        matches = self.method_query.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            if 'method.name' in captures:
                name_node = captures['method.name'][0]
                def_node = captures.get('method.def', captures.get('method.private', [None]))[0]
                
                if def_node:
                    # Find parent class
                    parent_class = self._find_parent_class_for_method(def_node)
                    parent_id = None
                    if parent_class and parent_class in class_symbols:
                        parent_id = class_symbols[parent_class]
                    
                    symbol = Symbol(
                        name=name_node.text.decode('utf-8'),
                        kind='method',
                        file=file_path,
                        line=name_node.start_point[0] + 1,
                        column=name_node.start_point[1],
                        end_line=def_node.end_point[0] + 1,
                        signature=self._extract_method_signature(def_node, source_code),
                        parent_id=parent_id
                    )
                    symbols.append(symbol)
        
        # Extract imports
        matches = self.import_query.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            # Import source (the module being imported from)
            if 'import.source' in captures:
                source_node = captures['import.source'][0]
                source_text = source_node.text.decode('utf-8')
                
                # Default imports
                if 'import.default' in captures:
                    name_node = captures['import.default'][0]
                    symbol = Symbol(
                        name=name_node.text.decode('utf-8'),
                        kind='import',
                        file=file_path,
                        line=name_node.start_point[0] + 1,
                        column=name_node.start_point[1],
                        signature=f"import {name_node.text.decode('utf-8')} from '{source_text}'"
                    )
                    symbols.append(symbol)
                
                # Named imports
                if 'import.name' in captures:
                    for name_node in captures['import.name']:
                        symbol = Symbol(
                            name=name_node.text.decode('utf-8'),
                            kind='import',
                            file=file_path,
                            line=name_node.start_point[0] + 1,
                            column=name_node.start_point[1],
                            signature=f"import {{ {name_node.text.decode('utf-8')} }} from '{source_text}'"
                        )
                        symbols.append(symbol)
                
                # Namespace imports
                if 'import.namespace' in captures:
                    name_node = captures['import.namespace'][0]
                    symbol = Symbol(
                        name=name_node.text.decode('utf-8'),
                        kind='import',
                        file=file_path,
                        line=name_node.start_point[0] + 1,
                        column=name_node.start_point[1],
                        signature=f"import * as {name_node.text.decode('utf-8')} from '{source_text}'"
                    )
                    symbols.append(symbol)
        
        # Extract exports
        matches = self.export_query.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            # Note: Exported functions/classes are already captured above
            # We could add an 'exported' flag to those symbols if needed
            
            # Handle re-exports
            if 'export.name' in captures:
                for name_node in captures['export.name']:
                    # Check if this is a re-export (not already defined)
                    name = name_node.text.decode('utf-8')
                    if not any(s.name == name for s in symbols):
                        symbol = Symbol(
                            name=name,
                            kind='export',
                            file=file_path,
                            line=name_node.start_point[0] + 1,
                            column=name_node.start_point[1],
                            signature=f"export {{ {name} }}"
                        )
                        symbols.append(symbol)
        
        return symbols
    
    def extract_edges(self, source_code: bytes, file_path: str, symbols: List[Symbol]) -> List[Edge]:
        """Extract dependency edges from JavaScript source code."""
        tree = self.parser.parse(source_code)
        edges = []
        
        # Create symbol lookup for this file
        symbol_names = {symbol.name for symbol in symbols}
        
        # Helper function to check if a symbol exists globally
        def symbol_exists_globally(name: str) -> bool:
            return bool(name and name != "<module>")
        
        # Extract function calls
        matches = self.call_query.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            caller = None
            called_function = None
            
            if 'call.name' in captures:
                # Simple function call
                call_node = captures['call.name'][0]
                called_function = call_node.text.decode('utf-8')
                caller = self._find_enclosing_function_or_method(call_node)
                
            elif 'call.method' in captures and 'call.object' in captures:
                # Method call
                method_node = captures['call.method'][0]
                object_node = captures['call.object'][0]
                called_function = method_node.text.decode('utf-8')
                object_name = object_node.text.decode('utf-8')
                caller = self._find_enclosing_function_or_method(method_node)
                
                if caller:
                    # Handle this.method() calls
                    if object_name == 'this':
                        if symbol_exists_globally(called_function):
                            edges.append(Edge(
                                from_symbol=caller,
                                to_symbol=called_function,
                                from_file=file_path,
                                to_file=file_path
                            ))
                    else:
                        # For any method call, create edge to the method
                        if symbol_exists_globally(called_function):
                            edges.append(Edge(
                                from_symbol=caller,
                                to_symbol=called_function,
                                from_file=file_path,
                                to_file=None  # Enable cross-file resolution
                            ))
                        
                        # Also create edge to the object
                        if symbol_exists_globally(object_name):
                            edges.append(Edge(
                                from_symbol=caller,
                                to_symbol=object_name,
                                from_file=file_path,
                                to_file=file_path
                            ))
            
            elif 'new.class' in captures:
                # Constructor call
                class_node = captures['new.class'][0]
                called_function = class_node.text.decode('utf-8')
                caller = self._find_enclosing_function_or_method(class_node)
            
            # Create edge if valid
            if caller and called_function and symbol_exists_globally(called_function):
                edges.append(Edge(
                    from_symbol=caller,
                    to_symbol=called_function,
                    from_file=file_path,
                    to_file=None  # Enable cross-file resolution
                ))
        
        # Extract member access dependencies
        matches = self.member_query.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            if 'member.object' in captures and 'member.property' in captures:
                object_node = captures['member.object'][0]
                property_node = captures['member.property'][0]
                object_name = object_node.text.decode('utf-8')
                property_name = property_node.text.decode('utf-8')
                
                caller = self._find_enclosing_function_or_method(object_node)
                
                if caller:
                    if symbol_exists_globally(object_name):
                        edges.append(Edge(
                            from_symbol=caller,
                            to_symbol=object_name,
                            from_file=file_path,
                            to_file=file_path
                        ))
                    if symbol_exists_globally(property_name):
                        edges.append(Edge(
                            from_symbol=caller,
                            to_symbol=property_name,
                            from_file=file_path,
                            to_file=None  # Enable cross-file resolution
                        ))
        
        # Extract assignment dependencies
        matches = self.assignment_query.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            if 'assign.function' in captures:
                # Variable assigned from function call
                function_node = captures['assign.function'][0]
                function_name = function_node.text.decode('utf-8')
                
                caller = self._find_enclosing_function_or_method(function_node)
                if caller and symbol_exists_globally(function_name):
                    edges.append(Edge(
                        from_symbol=caller,
                        to_symbol=function_name,
                        from_file=file_path,
                        to_file=None  # Enable cross-file resolution
                    ))
            
            elif 'assign.class' in captures:
                # Variable assigned from class instantiation
                class_node = captures['assign.class'][0]
                class_name = class_node.text.decode('utf-8')
                
                caller = self._find_enclosing_function_or_method(class_node)
                if caller and symbol_exists_globally(class_name):
                    edges.append(Edge(
                        from_symbol=caller,
                        to_symbol=class_name,
                        from_file=file_path,
                        to_file=None  # Enable cross-file resolution
                    ))
        
        return edges
    
    def _extract_function_signature(self, func_node: tree_sitter.Node, source_code: bytes) -> str:
        """Extract function signature from function node."""
        try:
            # Find the function header (up to the opening brace)
            start_byte = func_node.start_byte
            end_byte = func_node.start_byte
            
            # Find the opening brace
            brace_count = 0
            while end_byte < len(source_code):
                if source_code[end_byte:end_byte+1] == b'{':
                    brace_count += 1
                    if brace_count == 1:
                        break
                end_byte += 1
            
            signature_bytes = source_code[start_byte:end_byte]
            return signature_bytes.decode('utf-8', errors='ignore').strip()
        except:
            return ""
    
    def _extract_method_signature(self, method_node: tree_sitter.Node, source_code: bytes) -> str:
        """Extract method signature from method node."""
        try:
            # For methods, we want just the method name and parameters
            start_byte = method_node.start_byte
            end_byte = method_node.start_byte
            
            # Find the opening parenthesis and then the closing one
            paren_count = 0
            found_first_paren = False
            while end_byte < len(source_code):
                char = source_code[end_byte:end_byte+1]
                if char == b'(':
                    found_first_paren = True
                    paren_count += 1
                elif char == b')' and found_first_paren:
                    paren_count -= 1
                    if paren_count == 0:
                        end_byte += 1
                        break
                end_byte += 1
            
            signature_bytes = source_code[start_byte:end_byte]
            return signature_bytes.decode('utf-8', errors='ignore').strip()
        except:
            return ""
    
    def _find_parent_class_for_method(self, method_node: tree_sitter.Node) -> str:
        """Find the parent class name for a method."""
        current = method_node.parent
        
        while current:
            if current.type in ['class_declaration', 'class_expression']:
                # Find the class name
                for child in current.children:
                    if child.type == 'identifier':
                        return child.text.decode('utf-8')
            current = current.parent
        
        return None
    
    def _find_enclosing_function_or_method(self, node: tree_sitter.Node) -> str:
        """Find the name of the function/method that encloses this node."""
        current = node.parent
        class_name = None
        
        while current:
            if current.type in ['function_declaration', 'function_expression']:
                # Find the function name
                for child in current.children:
                    if child.type == 'identifier':
                        func_name = child.text.decode('utf-8')
                        
                        # If we found a class, prefix the method name
                        if class_name:
                            return f"{class_name}.{func_name}"
                        return func_name
                
                # For anonymous functions, check if assigned to a variable
                parent = current.parent
                if parent and parent.type == 'variable_declarator':
                    for child in parent.children:
                        if child.type == 'identifier':
                            func_name = child.text.decode('utf-8')
                            if class_name:
                                return f"{class_name}.{func_name}"
                            return func_name
                
            elif current.type == 'method_definition':
                # Find the method name
                for child in current.children:
                    if child.type in ['property_identifier', 'private_property_identifier']:
                        method_name = child.text.decode('utf-8')
                        
                        # Find the parent class
                        parent_class = self._find_parent_class_for_method(current)
                        if parent_class:
                            return f"{parent_class}.{method_name}"
                        return method_name
                
            elif current.type in ['class_declaration', 'class_expression'] and not class_name:
                # Remember the class name for method qualification
                for child in current.children:
                    if child.type == 'identifier':
                        class_name = child.text.decode('utf-8')
                        break
            
            current = current.parent
        
        # If no enclosing function found, return module-level indicator
        return "<module>"
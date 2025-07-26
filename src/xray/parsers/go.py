"""Go parser using Tree-sitter for XRAY."""

import tree_sitter
from typing import List, Set
from .base import LanguageParser, Symbol, Edge


class GoParser(LanguageParser):
    """Parser for Go source code."""
    
    def __init__(self, language: tree_sitter.Language):
        """Initialize Go parser."""
        super().__init__(language)
        
        # Tree-sitter queries for Go symbols
        self.function_query = tree_sitter.Query(self.language, """
            (function_declaration
                name: (identifier) @function.name
            ) @function.def
            
            (method_declaration
                receiver: (parameter_list
                    (parameter_declaration
                        type: (pointer_type
                            (type_identifier) @method.receiver
                        )
                    )
                ) @method.pointer_receiver
                name: (field_identifier) @method.name
            ) @method.def
            
            (method_declaration
                receiver: (parameter_list
                    (parameter_declaration
                        type: (type_identifier) @method.receiver
                    )
                ) @method.value_receiver
                name: (field_identifier) @method.name
            ) @method.value_def
        """)
        
        # Type declarations (structs, interfaces)
        self.type_query = tree_sitter.Query(self.language, """
            (type_declaration
                (type_spec
                    name: (type_identifier) @type.name
                    type: (struct_type) @type.struct
                )
            ) @struct.def
            
            (type_declaration
                (type_spec
                    name: (type_identifier) @type.name
                    type: (interface_type) @type.interface
                )
            ) @interface.def
            
            (type_declaration
                (type_spec
                    name: (type_identifier) @type.name
                    type: (_) @type.alias
                )
            ) @type.alias_def
        """)
        
        # Import declarations
        self.import_query = tree_sitter.Query(self.language, """
            (import_declaration
                (import_spec
                    path: (interpreted_string_literal) @import.path
                )
            ) @import.single
            
            (import_declaration
                (import_spec
                    name: (package_identifier) @import.alias
                    path: (interpreted_string_literal) @import.path
                )
            ) @import.aliased
            
            (import_declaration
                (import_spec_list
                    (import_spec
                        path: (interpreted_string_literal) @import.path
                    )
                )
            ) @import.list
            
            (import_declaration
                (import_spec_list
                    (import_spec
                        name: (package_identifier) @import.alias
                        path: (interpreted_string_literal) @import.path
                    )
                )
            ) @import.aliased_list
        """)
        
        # Variable declarations
        self.var_query = tree_sitter.Query(self.language, """
            (var_declaration
                (var_spec
                    name: (identifier) @var.name
                )
            ) @var.def
            
            (short_var_declaration
                left: (identifier_list
                    (identifier) @short.var.name
                )
            ) @short.var.def
            
            (const_declaration
                (const_spec
                    name: (identifier) @const.name
                )
            ) @const.def
        """)
        
        # Function calls
        self.call_query = tree_sitter.Query(self.language, """
            (call_expression
                function: (identifier) @call.name
            ) @call.expr
            
            (call_expression
                function: (selector_expression
                    operand: (identifier) @call.receiver
                    field: (field_identifier) @call.method
                )
            ) @call.method_expr
            
            (call_expression
                function: (selector_expression
                    operand: (selector_expression) @call.chained
                    field: (field_identifier) @call.chained_method
                )
            ) @call.chained_expr
        """)
        
        # Type instantiation
        self.instantiation_query = tree_sitter.Query(self.language, """
            (composite_literal
                type: (type_identifier) @new.type
            ) @new.literal
            
            (composite_literal
                type: (pointer_type
                    (type_identifier) @new.pointer_type
                )
            ) @new.pointer_literal
            
            (composite_literal
                type: (qualified_type
                    package: (package_identifier) @new.package
                    name: (type_identifier) @new.qualified_type
                )
            ) @new.qualified_literal
        """)
        
        # Selector expressions (field/method access)
        self.selector_query = tree_sitter.Query(self.language, """
            (selector_expression
                operand: (identifier) @selector.receiver
                field: (field_identifier) @selector.field
            ) @selector.expr
            
            (selector_expression
                operand: (selector_expression) @selector.chained
                field: (field_identifier) @selector.chained_field
            ) @selector.chained_expr
        """)
        
        # Type references
        self.type_reference_query = tree_sitter.Query(self.language, """
            (type_identifier) @type.ref
            
            (qualified_type
                package: (package_identifier) @qualified.package
                name: (type_identifier) @qualified.type
            ) @qualified.ref
        """)
    
    def extract_symbols(self, source_code: bytes, file_path: str) -> List[Symbol]:
        """Extract symbols from Go source code."""
        tree = self.parser.parse(source_code)
        symbols = []
        
        # Extract functions and methods
        query_cursor = tree_sitter.QueryCursor(self.function_query)
        matches = query_cursor.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            # Regular functions
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
            
            # Methods
            elif 'method.name' in captures and ('method.def' in captures or 'method.value_def' in captures):
                name_node = captures['method.name'][0]
                def_node = captures.get('method.def', captures.get('method.value_def', [None]))[0]
                
                if def_node:
                    # Get receiver type
                    receiver_type = None
                    if 'method.receiver' in captures:
                        receiver_node = captures['method.receiver'][0]
                        receiver_type = receiver_node.text.decode('utf-8')
                    
                    signature = self._extract_method_signature(def_node, source_code)
                    
                    # For now, we'll create methods as standalone symbols
                    # In Go, methods are not nested inside structs syntactically
                    symbol = Symbol(
                        name=name_node.text.decode('utf-8'),
                        kind='method',
                        file=file_path,
                        line=name_node.start_point[0] + 1,
                        column=name_node.start_point[1],
                        end_line=def_node.end_point[0] + 1,
                        signature=signature
                    )
                    symbols.append(symbol)
        
        # Extract types (structs, interfaces, type aliases)
        type_symbols = {}  # Track type symbols
        query_cursor = tree_sitter.QueryCursor(self.type_query)
        matches = query_cursor.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            if 'type.name' in captures:
                name_node = captures['type.name'][0]
                type_name = name_node.text.decode('utf-8')
                
                # Determine type kind
                kind = 'type'
                signature = f"type {type_name}"
                
                if 'type.struct' in captures:
                    kind = 'struct'
                    signature = f"type {type_name} struct"
                elif 'type.interface' in captures:
                    kind = 'interface'
                    signature = f"type {type_name} interface"
                
                # Get the full type declaration node
                def_node = captures.get('struct.def', captures.get('interface.def', captures.get('type.alias_def', [None])))[0]
                
                if def_node:
                    symbol = Symbol(
                        name=type_name,
                        kind=kind,
                        file=file_path,
                        line=name_node.start_point[0] + 1,
                        column=name_node.start_point[1],
                        end_line=def_node.end_point[0] + 1,
                        signature=signature
                    )
                    symbols.append(symbol)
                    type_symbols[type_name] = len(symbols) - 1
        
        # Extract imports
        query_cursor = tree_sitter.QueryCursor(self.import_query)
        matches = query_cursor.matches(tree.root_node)
        imported_packages = set()  # Track imported packages to avoid duplicates
        
        for match in matches:
            captures = match[1]
            
            if 'import.path' in captures:
                for path_node in captures['import.path']:
                    import_path = path_node.text.decode('utf-8').strip('"')
                    
                    # Extract package name from path
                    package_name = import_path.split('/')[-1]
                    
                    # Check if there's an alias
                    alias = None
                    if 'import.alias' in captures:
                        alias_nodes = captures['import.alias']
                        # Find the alias that corresponds to this import
                        for alias_node in alias_nodes:
                            # Simple heuristic: use line number to match
                            if abs(alias_node.start_point[0] - path_node.start_point[0]) <= 1:
                                alias = alias_node.text.decode('utf-8')
                                break
                    
                    import_name = alias if alias else package_name
                    signature = f'import "{import_path}"'
                    if alias:
                        signature = f'import {alias} "{import_path}"'
                    
                    # Avoid duplicate imports
                    if import_name not in imported_packages:
                        imported_packages.add(import_name)
                        
                        symbol = Symbol(
                            name=import_name,
                            kind='import',
                            file=file_path,
                            line=path_node.start_point[0] + 1,
                            column=path_node.start_point[1],
                            signature=signature
                        )
                        symbols.append(symbol)
        
        # Extract variables and constants
        query_cursor = tree_sitter.QueryCursor(self.var_query)
        matches = query_cursor.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            # Regular variable declarations
            if 'var.name' in captures:
                for name_node in captures['var.name']:
                    symbol = Symbol(
                        name=name_node.text.decode('utf-8'),
                        kind='variable',
                        file=file_path,
                        line=name_node.start_point[0] + 1,
                        column=name_node.start_point[1],
                        signature=f"var {name_node.text.decode('utf-8')}"
                    )
                    symbols.append(symbol)
            
            # Short variable declarations
            elif 'short.var.name' in captures:
                for name_node in captures['short.var.name']:
                    symbol = Symbol(
                        name=name_node.text.decode('utf-8'),
                        kind='variable',
                        file=file_path,
                        line=name_node.start_point[0] + 1,
                        column=name_node.start_point[1],
                        signature=f"{name_node.text.decode('utf-8')} :="
                    )
                    symbols.append(symbol)
            
            # Constants
            elif 'const.name' in captures:
                for name_node in captures['const.name']:
                    symbol = Symbol(
                        name=name_node.text.decode('utf-8'),
                        kind='constant',
                        file=file_path,
                        line=name_node.start_point[0] + 1,
                        column=name_node.start_point[1],
                        signature=f"const {name_node.text.decode('utf-8')}"
                    )
                    symbols.append(symbol)
        
        return symbols
    
    def extract_edges(self, source_code: bytes, file_path: str, symbols: List[Symbol]) -> List[Edge]:
        """Extract dependency edges from Go source code."""
        tree = self.parser.parse(source_code)
        edges = []
        
        # Create symbol lookup for this file
        symbol_names = {symbol.name for symbol in symbols}
        
        # Helper function to check if a symbol exists globally
        def symbol_exists_globally(name: str) -> bool:
            return bool(name and name not in {"<module>", "init", "main"})
        
        # Extract function calls
        query_cursor = tree_sitter.QueryCursor(self.call_query)
        matches = query_cursor.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            caller = None
            called_function = None
            
            if 'call.name' in captures:
                # Simple function call
                call_node = captures['call.name'][0]
                called_function = call_node.text.decode('utf-8')
                caller = self._find_enclosing_function(call_node)
                
            elif 'call.method' in captures and 'call.receiver' in captures:
                # Method call
                method_node = captures['call.method'][0]
                receiver_node = captures['call.receiver'][0]
                called_function = method_node.text.decode('utf-8')
                receiver_name = receiver_node.text.decode('utf-8')
                caller = self._find_enclosing_function(method_node)
                
                if caller:
                    # Create edge to the method
                    if symbol_exists_globally(called_function):
                        edges.append(Edge(
                            from_symbol=caller,
                            to_symbol=called_function,
                            from_file=file_path,
                            to_file=None  # Enable cross-file resolution
                        ))
                    
                    # Create edge to the receiver
                    if symbol_exists_globally(receiver_name):
                        edges.append(Edge(
                            from_symbol=caller,
                            to_symbol=receiver_name,
                            from_file=file_path,
                            to_file=file_path
                        ))
            
            # Create edge if valid
            if caller and called_function and symbol_exists_globally(called_function):
                edges.append(Edge(
                    from_symbol=caller,
                    to_symbol=called_function,
                    from_file=file_path,
                    to_file=None  # Enable cross-file resolution
                ))
        
        # Extract type instantiations
        query_cursor = tree_sitter.QueryCursor(self.instantiation_query)
        matches = query_cursor.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            caller = None
            type_name = None
            
            if 'new.type' in captures:
                type_node = captures['new.type'][0]
                type_name = type_node.text.decode('utf-8')
                caller = self._find_enclosing_function(type_node)
                
            elif 'new.pointer_type' in captures:
                type_node = captures['new.pointer_type'][0]
                type_name = type_node.text.decode('utf-8')
                caller = self._find_enclosing_function(type_node)
                
            elif 'new.qualified_type' in captures and 'new.package' in captures:
                type_node = captures['new.qualified_type'][0]
                package_node = captures['new.package'][0]
                type_name = type_node.text.decode('utf-8')
                package_name = package_node.text.decode('utf-8')
                caller = self._find_enclosing_function(type_node)
                
                if caller:
                    # Create edge to the package
                    if symbol_exists_globally(package_name):
                        edges.append(Edge(
                            from_symbol=caller,
                            to_symbol=package_name,
                            from_file=file_path,
                            to_file=None
                        ))
            
            # Create edge to the type
            if caller and type_name and symbol_exists_globally(type_name):
                edges.append(Edge(
                    from_symbol=caller,
                    to_symbol=type_name,
                    from_file=file_path,
                    to_file=None  # Enable cross-file resolution
                ))
        
        # Extract selector expressions (field/method access)
        query_cursor = tree_sitter.QueryCursor(self.selector_query)
        matches = query_cursor.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            if 'selector.receiver' in captures and 'selector.field' in captures:
                receiver_node = captures['selector.receiver'][0]
                field_node = captures['selector.field'][0]
                receiver_name = receiver_node.text.decode('utf-8')
                field_name = field_node.text.decode('utf-8')
                
                caller = self._find_enclosing_function(receiver_node)
                
                if caller:
                    if symbol_exists_globally(receiver_name):
                        edges.append(Edge(
                            from_symbol=caller,
                            to_symbol=receiver_name,
                            from_file=file_path,
                            to_file=file_path
                        ))
                    if symbol_exists_globally(field_name):
                        edges.append(Edge(
                            from_symbol=caller,
                            to_symbol=field_name,
                            from_file=file_path,
                            to_file=None  # Enable cross-file resolution
                        ))
        
        # Extract type references
        query_cursor = tree_sitter.QueryCursor(self.type_reference_query)
        matches = query_cursor.matches(tree.root_node)
        for match in matches:
            captures = match[1]
            
            if 'type.ref' in captures:
                type_node = captures['type.ref'][0]
                type_name = type_node.text.decode('utf-8')
                
                # Skip built-in types
                if type_name not in {'string', 'int', 'int8', 'int16', 'int32', 'int64',
                                   'uint', 'uint8', 'uint16', 'uint32', 'uint64',
                                   'float32', 'float64', 'bool', 'byte', 'rune',
                                   'error', 'interface{}', 'any'}:
                    caller = self._find_enclosing_function(type_node)
                    if caller and symbol_exists_globally(type_name):
                        edges.append(Edge(
                            from_symbol=caller,
                            to_symbol=type_name,
                            from_file=file_path,
                            to_file=None
                        ))
            
            elif 'qualified.type' in captures and 'qualified.package' in captures:
                type_node = captures['qualified.type'][0]
                package_node = captures['qualified.package'][0]
                type_name = type_node.text.decode('utf-8')
                package_name = package_node.text.decode('utf-8')
                
                caller = self._find_enclosing_function(type_node)
                if caller:
                    # Create edge to the type
                    if symbol_exists_globally(type_name):
                        edges.append(Edge(
                            from_symbol=caller,
                            to_symbol=type_name,
                            from_file=file_path,
                            to_file=None
                        ))
                    # Create edge to the package
                    if symbol_exists_globally(package_name):
                        edges.append(Edge(
                            from_symbol=caller,
                            to_symbol=package_name,
                            from_file=file_path,
                            to_file=None
                        ))
        
        return edges
    
    def _extract_function_signature(self, func_node: tree_sitter.Node, source_code: bytes) -> str:
        """Extract function signature from function node."""
        try:
            # Find the function declaration up to the opening brace
            start_byte = func_node.start_byte
            end_byte = func_node.start_byte
            
            # Find the opening brace
            while end_byte < len(source_code):
                if source_code[end_byte:end_byte+1] == b'{':
                    break
                end_byte += 1
            
            signature_bytes = source_code[start_byte:end_byte]
            return signature_bytes.decode('utf-8', errors='ignore').strip()
        except:
            return ""
    
    def _extract_method_signature(self, method_node: tree_sitter.Node, source_code: bytes) -> str:
        """Extract method signature from method node."""
        try:
            # For methods, include the receiver
            start_byte = method_node.start_byte
            end_byte = method_node.start_byte
            
            # Find the opening brace
            while end_byte < len(source_code):
                if source_code[end_byte:end_byte+1] == b'{':
                    break
                end_byte += 1
            
            signature_bytes = source_code[start_byte:end_byte]
            return signature_bytes.decode('utf-8', errors='ignore').strip()
        except:
            return ""
    
    def _find_enclosing_function(self, node: tree_sitter.Node) -> str:
        """Find the name of the function/method that encloses this node."""
        current = node.parent
        
        while current:
            if current.type == 'function_declaration':
                # Find the function name
                for child in current.children:
                    if child.type == 'identifier':
                        return child.text.decode('utf-8')
                
            elif current.type == 'method_declaration':
                # Find the method name
                for child in current.children:
                    if child.type == 'field_identifier':
                        method_name = child.text.decode('utf-8')
                        
                        # Try to get receiver type for qualified name
                        receiver_type = self._get_method_receiver_type(current)
                        if receiver_type:
                            return f"{receiver_type}.{method_name}"
                        return method_name
            
            current = current.parent
        
        # Check if we're at package level
        return "<module>"
    
    def _get_method_receiver_type(self, method_node: tree_sitter.Node) -> str:
        """Get the receiver type for a method."""
        for child in method_node.children:
            if child.type == 'parameter_list':
                # Look for the receiver parameter
                for param_child in child.children:
                    if param_child.type == 'parameter_declaration':
                        # Find the type
                        for type_child in param_child.children:
                            if type_child.type == 'type_identifier':
                                return type_child.text.decode('utf-8')
                            elif type_child.type == 'pointer_type':
                                # For pointer receivers, get the underlying type
                                for ptr_child in type_child.children:
                                    if ptr_child.type == 'type_identifier':
                                        return ptr_child.text.decode('utf-8')
        return None
import os
from typing import List, Dict

class Calculator:
    def add(self, a: int, b: int) -> int:
        return a + b
    
    def multiply(self, x: float, y: float) -> float:
        result = x * y
        return result

def process_items(items: List[Dict]) -> Dict:
    calculator = Calculator()
    total = 0
    
    for item in items:
        value = item.get("value", 0)
        total = calculator.add(total, value)
    
    return {"total": total, "count": len(items)}

if __name__ == "__main__":
    test_data = [{"value": 10}, {"value": 20}]
    result = process_items(test_data)
    print(result)
EOF < /dev/null

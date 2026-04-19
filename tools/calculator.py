import ast
import math
import operator

_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

_SAFE_FUNCS = {k: getattr(math, k) for k in dir(math) if not k.startswith("_")}
_SAFE_FUNCS.update({"abs": abs, "round": round, "min": min, "max": max, "sum": sum})


def _eval_node(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        op = _SAFE_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op(_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp):
        op = _SAFE_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        return op(_eval_node(node.operand))
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only simple function calls allowed")
        fn = _SAFE_FUNCS.get(node.func.id)
        if fn is None:
            raise ValueError(f"Unknown function: {node.func.id}")
        args = [_eval_node(a) for a in node.args]
        return fn(*args)
    if isinstance(node, ast.Name):
        val = _SAFE_FUNCS.get(node.id)
        if val is None:
            raise ValueError(f"Unknown name: {node.id}")
        return val
    raise ValueError(f"Unsupported expression type: {type(node).__name__}")


async def calculate(expression: str) -> str:
    """Evaluate a math expression safely (supports +,-,*,/,**,%, trig, log, sqrt, etc.)."""
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _eval_node(tree.body)
        if isinstance(result, float) and result == int(result) and abs(result) < 1e15:
            result = int(result)
        return f"{expression} = {result}"
    except Exception as e:
        return f"Calculation error: {e}"

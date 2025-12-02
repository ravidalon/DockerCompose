from flask import Flask, request, jsonify
from werkzeug.wrappers.response import Response as WerkzeugResponse
import math

app = Flask(__name__)


@app.route('/calculate', methods=['POST'])
def calculate() -> tuple[WerkzeugResponse, int]:
    """Calculator endpoint that evaluates mathematical expressions"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    expression = data.get('expression')
    if not expression:
        return jsonify({"error": "No expression provided"}), 400

    disallowed_operators = ['^', '&', '|', '~', '<<', '>>']
    for op in disallowed_operators:
        if op in expression:
            return jsonify({"error": f"Operator '{op}' is not supported. Use ** for power."}), 400

    try:
        safe_dict = {
            '__builtins__': {},
            'abs': abs,
            'round': round,
            'min': min,
            'max': max,
            'sum': sum,
            'pow': pow,
            'sqrt': math.sqrt,
            'sin': math.sin,
            'cos': math.cos,
            'tan': math.tan,
            'pi': math.pi,
            'e': math.e,
        }
        result = eval(expression, safe_dict)
        return jsonify({"expression": expression, "result": str(result)}), 200
    except Exception as e:
        return jsonify({"error": f"Invalid expression: {str(e)}"}), 400


@app.route('/health', methods=['GET'])
def health() -> tuple[WerkzeugResponse, int]:
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

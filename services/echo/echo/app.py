from flask import Flask, request, jsonify
from werkzeug.wrappers.response import Response as WerkzeugResponse

app = Flask(__name__)


@app.route('/echo', methods=['POST'])
def echo() -> tuple[WerkzeugResponse, int]:
    """Echo endpoint that returns the data sent to it"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    return jsonify(data), 200


@app.route('/health', methods=['GET'])
def health() -> tuple[WerkzeugResponse, int]:
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

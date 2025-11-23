from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/echo', methods=['POST'])
def echo():
    """Echo endpoint that returns the data sent to it"""
    data = request.get_json()

    if not data:
        return jsonify({"error": "No data provided"}), 400

    return jsonify(data), 200

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

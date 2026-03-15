from flask import Flask
import os
import threading

app = Flask(__name__)

@app.route('/')
@app.route('/health')
@app.route('/healthcheck')
def health():
    return "OK", 200

def run_health_server():
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# Запускаем сервер в фоновом потоке при импорте
threading.Thread(target=run_health_server, daemon=True).start()
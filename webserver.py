from flask import Flask
import threading

app = Flask(__name__)

@app.route('/')
def hello_world():
    return 'Bot is running!'

def run_server():
    app.run(host='0.0.0.0', port=8080)

def start_web_server():
    thread = threading.Thread(target=run_server)
    thread.daemon = True
    thread.start()
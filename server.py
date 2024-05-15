from flask import Flask, request, render_template_string, jsonify, url_for, redirect
from flask_socketio import SocketIO
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

socketio = SocketIO(app)


EXAMPLE_WEBHOOK_STRING = 'my-webhook'

@app.route('/')
def home():
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Webhook Tester</title>
</head>
<body>
    <h1>Webhook Tester</h1>
    <p>Enter a URL to create a webhook endpoint.</p>
    <p>Messages sent to the endpoint will be displayed in the console.</p>
    <p>Example: using "{EXAMPLE_WEBHOOK_STRING}" will create an API endpoint at "{url_for('api_endpoint', url_string=EXAMPLE_WEBHOOK_STRING, _external=True)}", 
    and all requests to this API endpoint will be logged at "{url_for('webhook_console', url_string=EXAMPLE_WEBHOOK_STRING, _external=True)}".</p>
    <form action="/create_endpoint" method="post">
        <input type="text" name="url_string" id="url_string" required>
        <button type="submit">Create Webhook Endpoint</button>
    </form>
</body>
</html>
"""

@app.route('/create_endpoint', methods=['POST'])
def create_endpoint():
    url_string = request.form['url_string']
    return redirect(url_for('webhook_console', url_string=url_string))

@app.route('/console/<url_string>')
def webhook_console(url_string):
    return render_template_string(f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Webhook Tester</title>
            <script src="https://cdn.socket.io/4.7.5/socket.io.min.js" integrity="sha384-2huaZvOR9iDzHqslqwpR87isEmrfxqyWOF7hr7BY6KG0+hVKLoEXMPUJw3ynWuhO" crossorigin="anonymous"></script>        
            <script type="text/javascript">
            document.addEventListener('DOMContentLoaded', function () {{
                console.log('DOM loaded');
                var socket = io();
                socket.on('connect', function() {{
                    socket.emit('join', {{}});
                    console.log('Websocket connected to server');
                }});
                socket.on('message', function(data) {{
                    console.log(data.msg);
                    if (data.url_string === "{url_string}") {{
                        var node = document.createElement("LI");
                        var textnode = document.createTextNode(data.msg);
                        node.appendChild(textnode);
                        document.getElementById("messages").appendChild(node);
                    }}
                }});
                socket.on("connect_error", (err) => {{
                  console.log(`websocket connect_error`);
                  console.log(err.message);
                  console.log(err.description);
                  console.log(err.context);
                }});
            }});
        </script>
    </head>
    <body>
        <h1>Webhook Tester</h1>
        <p>Messages received on {url_for('api_endpoint', url_string=url_string, _external=True)}</p>
        <ul id="messages"></ul>
    </body>
    </html>
    """)

@app.route('/api/<path:url_string>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_endpoint(url_string):
    data = request.get_data(as_text=True) or f"No data received. Method: {request.method}"
    message = f"Received: {request.method} /api/{url_string}: {data}"
    socketio.emit('message', {'msg': message, 'url_string': url_string})
    print(message + f", url_string=/{url_string}")
    return jsonify(success=True)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0')

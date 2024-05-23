import datetime
import json
import pprint

import flask_socketio
from flask import Flask, request, render_template_string, jsonify, url_for, redirect
from flask_socketio import SocketIO
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'

app.wsgi_app = ProxyFix(
    app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1
)

socketio = SocketIO(app, engineio_logger=True)


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
    <p>Enter an identifier to create a webhook endpoint.</p>
    <p>Messages sent to the endpoint will be displayed in the console.</p>
    <p>Example: using "{EXAMPLE_WEBHOOK_STRING}" as the identifier will create an API endpoint at "{url_for('api_endpoint', url_string=EXAMPLE_WEBHOOK_STRING, _external=True)}", 
    and all requests to this API endpoint will be logged at "{url_for('webhook_console', url_string=EXAMPLE_WEBHOOK_STRING, _external=True)}".</p>
    <form action="/create_endpoint" method="post">
        <label for="url_string">{url_for('api_endpoint', url_string='', _external=True)}</label>
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
            <script src="https://cdn.socket.io/4.7.5/socket.io.js" crossorigin="anonymous"></script>        
            <script type="text/javascript">
            document.addEventListener('DOMContentLoaded', function () {{
                console.log('DOM loaded');
                var socket = io();
                socket.on('connect', function() {{
                    socket.emit('join', {{"url_string": "{url_string}"}});
                    console.log('Websocket connected to server');
                }});
                socket.on('message', function(data) {{
                    console.log(data);
                    
                    // Get the table body element
                    var tableBody = document.getElementById("messageTable").getElementsByTagName("tbody")[0];
                    
                    // Create a new row
                    var newRow = document.createElement("TR");
                    
                    // Create and append the timestamp cell
                    var timestampCell = document.createElement("TD");
                    timestampCell.appendChild(document.createTextNode(data.timestamp));
                    newRow.appendChild(timestampCell);
                    
                    // Create and append the method cell
                    var methodCell = document.createElement("TD");
                    methodCell.appendChild(document.createTextNode(data.method));
                    newRow.appendChild(methodCell);
                    
                    // Create and append the URL cell
                    var urlCell = document.createElement("TD");
                    urlCell.appendChild(document.createTextNode(data.url));
                    newRow.appendChild(urlCell);
                    
                    // Create and append the body cell
                    var bodyCell = document.createElement("TD");
                    var pre = document.createElement("PRE");
                    try {{
                        var jsonObj = JSON.parse(data.body);
                        pre.appendChild(document.createTextNode(JSON.stringify(jsonObj, null, 2)));
                    }} catch (e) {{
                        console.log(e);
                        console.log('Failed to parse JSON, displaying raw text');
                        pre.appendChild(document.createTextNode(data.body));
                    }}
                    bodyCell.appendChild(pre);
                    newRow.appendChild(bodyCell);
                    
                    // Append the new row to the table body
                    tableBody.appendChild(newRow);
                }});
                socket.on("connect_error", (err) => {{
                  console.log(`websocket connect_error`);
                  console.log(err);
                  console.log(err.message);
                  console.log(err.description);
                  console.log(err.context);
                }});
                socket.on("disconnect", (reason, details) => {{
                  // the reason of the disconnection, for example "transport error"
                  console.log(reason);
                  console.log(details);
                  // the low-level reason of the disconnection, for example "xhr post error"
                  console.log(details.message);
                  // some additional description, for example the status code of the HTTP response
                  console.log(details.description);
                  // some additional context, for example the XMLHttpRequest object
                  console.log(details.context);
                }});
            }});
        </script>
        <style>
            table, th, td {{
                border: 1px solid black;
                border-collapse: collapse;
                padding: 4px;
            }}
            pre {{
                font-family: monospace;
                margin: 0;
            }}
            tr:nth-child(even) {{
                background-color: lightgrey;
            }}
        </style>
    </head>
    <body>
        <h1>Webhook Tester</h1>
        <p>Messages received on {url_for('api_endpoint', url_string=url_string, _external=True)}</p>
        <table id="messageTable">
            <thead>
                <tr>
                    <th>Timestamp</th>
                    <th>Method</th>
                    <th>URL</th>
                    <th>Body</th>
                </tr>
            </thead>
            <tbody>
                <!-- Rows will be added here dynamically -->
            </tbody>
        </table>
    </body>
    </html>
    """)

@app.route('/api/<path:url_string>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_endpoint(url_string):
    data = request.get_data(as_text=True) or f"No data received. Method: {request.method}"
    message = f"Received: {request.method} /api/{url_string}: {data}"

    socket_data = {
        'msg': message,
        'timestamp': str(datetime.datetime.now()),
        'method': request.method,
        'url': f"/api/{url_string}",
        'body': request.get_data(as_text=True) or None,
        'url_string': url_string
    }

    socketio.emit('message', socket_data, to=url_string)
    print(f"{socket_data}, url_string=/{url_string}")
    return jsonify(success=True)

@socketio.on('join')
def on_socket_join_room(data):
    print(f"client joined room with data = {data}")
    flask_socketio.join_room(data['url_string'])

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0')

# dashboard.py
# ----------------------------------------------------------
# Digital Twin Dashboard with enc_fields display
# ----------------------------------------------------------

import json
import time
import threading
import collections
import paho.mqtt.client as mqtt
import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go


BROKER = "127.0.0.1"
PORT = 1883
TOPIC = "dt/test"

BUF_SIZE = 300
buf = collections.deque(maxlen=BUF_SIZE)
lock = threading.Lock()


def on_message(client, userdata, message):
    try:
        data = json.loads(message.payload.decode("utf-8"))
        with lock:
            buf.append(data)
    except:
        pass


def mqtt_thread():
    c = mqtt.Client(client_id=f"dash-{int(time.time())}")
    c.on_message = on_message
    c.connect(BROKER, PORT, keepalive=30)
    c.subscribe(TOPIC, qos=0)
    c.loop_forever()



t = threading.Thread(target=mqtt_thread, daemon=True)
t.start()


app = dash.Dash(__name__)
app.layout = html.Div([
    html.H2("Digital Twin Dashboard"),

    dcc.Interval(id="tick", interval=500, n_intervals=0),

    dcc.Graph(id="temp_graph"),
    dcc.Graph(id="speed_graph"),

    html.H4("Latest Data"),
    html.Pre(id="latest", style={"background": "#f7f7f7", "padding": "8px"}),

    html.H4("Fields Marked for Encryption"),
    html.Pre(id="enc_fields", style={"background": "#f0f0f0", "padding": "8px"})
])


@app.callback(
    [Output("temp_graph", "figure"),
     Output("speed_graph", "figure"),
     Output("latest", "children"),
     Output("enc_fields", "children")],
    [Input("tick", "n_intervals")]
)
def update(_):
    with lock:
        data = list(buf)

    if not data:
        return go.Figure(), go.Figure(), "Waiting for data...", ""

    xs = [d.get("timestamp") for d in data]
    temps = [d.get("temperature") for d in data]
    speeds = [d.get("speed") for d in data]
    latest = data[-1]

    fig_t = go.Figure(data=[go.Scatter(x=xs, y=temps, mode="lines")])
    fig_t.update_layout(title="Temperature", xaxis_title="time", yaxis_title="°C")

    fig_s = go.Figure(data=[go.Scatter(x=xs, y=speeds, mode="lines")])
    fig_s.update_layout(title="Speed", xaxis_title="time", yaxis_title="rpm")

    pretty = json.dumps(latest, indent=2)
    enc_list = latest.get("_enc_header", {}).get("enc_fields", [])

    return fig_t, fig_s, pretty, json.dumps(enc_list, indent=2)


if __name__ == "__main__":
    app.run_server(debug=False, port=8050)

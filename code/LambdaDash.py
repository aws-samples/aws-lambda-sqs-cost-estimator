
import dash
from dash import dcc
from dash import html
from flask import Flask

import LambdaPlotly

server = Flask(__name__)
@server.route("/")

def main():

    fig = LambdaPlotly.processCalculations()
    fig.layout.height=1200

    app = dash.Dash(server=server,  url_base_pathname='/app/')
    app.layout = html.Div([
        dcc.Graph(figure=fig, responsive = 'auto', )
    ])

    app.run_server(port=8080, host='0.0.0.0', debug=True, use_reloader=False)  # Turn off reloader if inside Jupyter


if __name__ == "__main__":
    main()

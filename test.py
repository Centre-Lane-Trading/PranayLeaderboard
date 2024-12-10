import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import numpy as np

# Create a Dash app
app = dash.Dash(__name__)

# Generate sample data for the line graph
x = np.arange(1, 101)
y = np.sin(x / 5) + np.cos(x / 10)

# Create the layout for the Dash app
app.layout = html.Div([
    html.H1("Zoom and Fetch X-axis Values"),
    
    # Line chart using dcc.Graph
    dcc.Graph(
        id='line-graph',
        figure={
            'data': [go.Scatter(x=x, y=y, mode='lines')],
            'layout': go.Layout(
                title="Line Graph Example",
                xaxis={'title': 'X-axis'},
                yaxis={'title': 'Y-axis'},
                dragmode='zoom',  # Enables zooming
            )
        },
        config={'scrollZoom': True}  # Enable zooming with mouse scroll
    ),
    
    # Div to display the selected x-axis range
    html.Div(id='zoom-output', style={'marginTop': 20})
])

# Define callback to update output based on zoom (x-axis range)
@app.callback(
    Output('zoom-output', 'children'),
    Input('line-graph', 'relayoutData')
)
def display_zoom(relayoutData):
    print("Tue")
    print(relayoutData)
    # Check if the x-axis range is available in the relayoutData
    if 'xaxis.range' in relayoutData:
        x_range = relayoutData['xaxis.range']
        return f"Zoomed-in X-axis Range: {x_range}"
    else:
        return "Zoom out to see the x-axis range"

if __name__ == '__main__':
    app.run_server(debug=True)
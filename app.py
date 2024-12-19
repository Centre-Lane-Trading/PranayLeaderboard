from ast import Global
import dash
from dash import dcc, html, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import polars as pl
from datetime import datetime
import io
import base64
import pandas as pd
from logic import Leaderboard
import logic
from dash.exceptions import PreventUpdate
from datetime import date


# Initialize Leaderboard instance
board = logic.Leaderboard()
# Extract the min and max dates
min_date, max_date = board.get_date_range()

# Helper Functions
def create_figure(data, x_col, y_col, title, x_label, y_label, group_col="policy"):
    """
    Create a Plotly Figure from given data, with cumulative profit.
    """
    fig = go.Figure()
    
    # Define your policy colors
    policy_colors = {
        "PJMvirts Captain Hindsight": "#54C158",  # Green
        "PJMvirts Pricetaker Short": "#FFA800",   # Orange
        "PJMvirts Pricetaker Long": "#25A5FF"     # Blue
    }

    if data is not None and not data.is_empty():
        for group in data[group_col].unique():
            filtered_data = data.filter(pl.col(group_col) == group)

            # Sort data by date
            filtered_data = filtered_data.sort(x_col)

            # Calculate cumulative profit
            filtered_data = filtered_data.with_columns(
                pl.col(y_col).cum_sum().alias("cumulative_profit")
            )
            
            # Get the color for the current group, default to gray if not found
            line_color = policy_colors.get(group, "#A0A0A0")  # Default color if not found
            
            # Add trace for each policy with specific color
            fig.add_trace(go.Scatter(
                x=filtered_data[x_col].to_list(),
                y=filtered_data["cumulative_profit"].to_list(),
                mode="lines",
                name=group,
                line=dict(color=line_color)  # Set the line color
            ))

    # Update layout with titles and such
    fig.update_layout(title=title, xaxis_title=x_label, yaxis_title=y_label)
    return fig


def prepare_table_data(data):
    """
    Convert the Polars DataFrame to a list of dictionaries for Dash DataTable.
    """
    return data.to_dicts() if data is not None and not data.is_empty() else []

# Dash app setup
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css"])
app.title = "Trading Dashboard Dev"

# Define the colors for each policy (for chart and table)
policy_colors = {
    "Captain Hindsight": "#54C158",  # Green
    "Pricetaker Short": "#FFA800",   # Orange
    "Pricetaker Long": "#25A5FF"     # Blue
}

app.layout = html.Div([
    # Header
    html.Div(
        id = "header_title",
        className="header",
        style={"backgroundColor": "#4682B4", "color": "#003366", "padding": "10px", "textAlign": "center", "position": "relative"},
        children=[
            html.H1("Trading Dashboard Dev", style={"margin": "0", "textAlign": "center", "color": "#003366"}),
            html.I(className="fas fa-chart-bar", style={"position": "absolute", "right": "20px", "top": "50%", "transform": "translateY(-50%)", "fontSize": "24px", "color": "#003366"})
        ]
    ),
    
    # Main content container with chart and table
    html.Div(
        style={"display": "flex", "flexDirection": "row", "padding": "20px", "flexWrap": "wrap"},
        children=[
            # Left column: Chart and Wins vs Losses
            html.Div(
                style={"flex": "2", "padding": "10px", "minWidth": "300px"},
                children=[
                    dcc.Tabs(
                        id="tabs",
                        value="tab-1",
                        children=[
                            dcc.Tab(label="Profit Chart", value="tab-1"),
                            dcc.Tab(label="Wins vs Losses", value="tab-2")
                        ]
                    ),
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "justifyContent": "center", "marginTop": "20px"},
                        children=[
                            dcc.Dropdown(
                                id="chart-type-dropdown",
                                options=[
                                    {"label": "Total", "value": "profit_total"},
                                    {"label": "Short", "value": "profit_short"},
                                    {"label": "Long", "value": "profit_long"}
                                ],
                                value="profit_total",
                                clearable=False,
                                style={"width": "200px"}
                            ),
                            html.Div([
                                dbc.Checklist(
                                    options=[{"label": "Enable Area", "value": "enable"}],
                                    value=[],  # Initially unchecked
                                    id="area-toggle",
                                    switch=True,
                                    style={"marginLeft": "10px"},
                                    inline=True,
                                ),
                                html.Button(
                                    "Reset Chart",
                                    id="reset-chart-toggle-button",
                                    style={
                                        "marginLeft": "10px",
                                        "backgroundColor": "#4682B4",
                                        "border": "none",
                                        "color": "white",
                                        "padding": "10px",
                                        "borderRadius": "5px",
                                        "cursor": "pointer"
                                    },
                                    n_clicks=0,
                                )
                            ], id='toggle-area-container', style={"display":"none"}),
                        ]
                    ),
                    # Chart container and the content for selected tab
                    html.Div(
                        id="chart-container",
                        style={"marginBottom": "20px"},
                        children=[
                            dcc.Graph(
                                id="graph",  # This is the id referenced in the callback
                                config={"scrollZoom": True},  # Allow zooming
                                style={"height": "500px"},  # Set graph size
                            )
                        ],
                    ),
                    # Footer (Date range filter)
                    html.Div(
                        style={"marginTop": "20px", "textAlign": "center"},
                        children=[
                            dcc.Checklist(
                            id="date-range-checklist",
                            options=[{"label": "Enable Date Range Filter", "value": "date_range_enable"}],
                            value=[],  # Initially unchecked
                            style={"display": "inline-block"}
                        ),
                        html.Div(
                            id="slider-container",  # Wrapper div to control visibility
                            style={"display": "none"},  # Initially hidden
                            children=[
                                # Create the RangeSlider with dynamic date range
                               dcc.DatePickerRange(
                                    id="date-picker-range",
                                    start_date=min_date,  # Set default start date
                                    end_date=max_date,   # Set default end date
                                    display_format="YYYY-MM-DD",  # Format of the date display
                                    style={"margin": "10px", "width": "300px"}
                                ),
                                html.Button("Exclude Range", id="exclude-button", style={"marginLeft": "10px", "padding": "10px"}),
                                html.Button("Reset Excluded Ranges", id="reset-button", style={"marginLeft": "10px", "padding": "10px"})
                            ]
                        )]
                    ),
                    html.Div(
                        id="wins-losses-container"
                    ),
                ]
            ),
            
            # Right column: Dropdown, download button, and Table
            html.Div(
                style={"flex": "1", "padding": "10px", "minWidth": "300px"},
                children=[
                    html.Div(
                        style={"display": "flex", "alignItems": "center", "marginBottom": "20px"},
                        children=[
                            dcc.Dropdown(
                                id="download-dropdown",
                                options=[
                                    {"label": "Displayed Data", "value": "window_data"},
                                    {"label": "Exclusions Data", "value": "exclsion_data"},
                                    {"label": "Original Data", "value": "original_data"}
                                ],
                                value="Displayed Data",
                                placeholder="Select a model",
                                style={"flex": "1"}
                            ),
                            html.Button(
                                html.I(className="fas fa-download", style={"fontSize": "24px", "color": "white"}),
                                n_clicks=0,
                                id="download-button",
                                style={
                                    "marginLeft": "10px",
                                    "backgroundColor": "#4682B4",
                                    "border": "none",
                                    "color": "white",
                                    "padding": "10px",
                                    "borderRadius": "5px",
                                    "cursor": "pointer",
                                    "fontSize": "20px"

                                }
                            )
                        ]
                    ),
                    html.Div(
                        style={"flex": "1", "padding": "10px", "minWidth": "300px"},
                        children=[
                            dash_table.DataTable(
                                id="metric_table",
                                sort_action='native',
                                columns=[
                                    {"name": "Model Name", "id": "policy"},
                                    {"name": "Total Profit", "id": "PnL"},
                                    {"name": "Profit per MWh", "id": "per MWh"},
                                    {"name": "Win Percentage", "id": "win %"}
                                ],
                                style_table={"overflowX": "auto"},
                                style_cell={"padding": "10px", "textAlign": "center", "border": "1px solid #ddd"},
                                style_header={"backgroundColor": "#f4f4f4", "fontWeight": "bold"},
                                style_data_conditional=[
                                {
                                    "if": {"filter_query": '{policy} = "PJMvirts Captain Hindsight"'},  # Match value in "policy" column
                                    "backgroundColor": policy_colors["Captain Hindsight"],             # Green
                                    "color": "white"
                                },
                                {
                                    "if": {"filter_query": '{policy} = "PJMvirts Pricetaker Short"'},  # Match value in "policy" column
                                    "backgroundColor": policy_colors["Pricetaker Short"],              # Orange
                                    "color": "white"
                                },
                                {
                                    "if": {"filter_query": '{policy} = "PJMvirts Pricetaker Long"'},   # Match value in "policy" column
                                    "backgroundColor": policy_colors["Pricetaker Long"],               # Blue
                                    "color": "white"
                                }
                            ]
                            )
                        ]
                    ),
                    dcc.Download(id="download-dataframe-csv")
                ]
            )
        ]
    )
])


@app.callback(
    [Output("graph", "figure",allow_duplicate=True),
    Output("metric_table", "data",allow_duplicate=True),
    Output('toggle-area-container', 'style'),
    Output('area-toggle','value')
    ],
    [
    Input('reset-chart-toggle-button','n_clicks'),
    ],
    prevent_initial_call=True
)
def toggle_area(n_clicks):
    ctx = dash.callback_context
    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    if button_id =='reset-chart-toggle-button':
        # Fetch the data and summary from the board
        global board
        board = logic.Leaderboard() # Doing reset by initializing the class again
        summary_data = board.summarize()
        
        # Generate the chart using the helper function
        fig = create_figure(
            board.exclusions_df,
            x_col="date",
            y_col=board.chart_type,
            title="Leaderboard Data",
            x_label="Date",
            y_label="Profit Cumulative"
        )
        # Prepare the table data using the helper function
        summary_table_data = prepare_table_data(summary_data)
        return fig, summary_table_data, {'display': 'none'}, []
    return dash.no_update, dash.no_update, dash.no_update, dash.no_update

@app.callback(
    [Output("graph", "figure",allow_duplicate=True),
    Output("metric_table", "data",allow_duplicate=True),
     Output('toggle-area-container', 'style',allow_duplicate=True),
    ],
    [Input('graph', 'relayoutData'),
    ],
     State("area-toggle", "value"),
    prevent_initial_call=True
)
def pan_graph(relayoutData,area_toggle):
    if relayoutData:
        if ('xaxis.range[0]' in relayoutData or 'yaxis.range[0]' in relayoutData) and len(area_toggle)==0:

                start_date = relayoutData['xaxis.range[0]']
                end_date = relayoutData['xaxis.range[1]']
                # Convert the date string to a datetime object
                start_datetime_object = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S.%f")
                end_datetime_object = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S.%f")
                start_date_date_only = start_datetime_object.date()
                end_date_date_only = end_datetime_object.date()
                board.pan(start_date_date_only,end_date_date_only)
                # Prepare the table data using the helper function
                summary_data = board.summarize()
                summary_table_data = prepare_table_data(summary_data)
                return dash.no_update, summary_table_data, {'display': 'block'}
        elif ('xaxis.range[0]' in relayoutData or 'yaxis.range[0]' in relayoutData) and len(area_toggle)>0:
                start_date = relayoutData['xaxis.range[0]']
                end_date = relayoutData['xaxis.range[1]']
                # Convert the date string to a datetime object
                start_datetime_object = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S.%f")
                end_datetime_object = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S.%f")
                start_date_date_only = start_datetime_object.date()
                end_date_date_only = end_datetime_object.date()
                board.pan(start_date_date_only,end_date_date_only)
                # Generate the chart using the helper function
                fig = create_figure(
                    board.window,
                    x_col="date",
                    y_col=board.chart_type,
                    title="Leaderboard Data",
                    x_label="Date",
                    y_label="Profit Cumulative"
                )
                # Prepare the table data using the helper function
                summary_data = board.summarize()
                summary_table_data = prepare_table_data(summary_data)
                return fig, summary_table_data, {'display': 'block'}
    return dash.no_update, dash.no_update, dash.no_update

@app.callback(
    [
        Output("graph", "figure",allow_duplicate=True),
        Output("metric_table", "data",allow_duplicate=True),
    ],
    [
        Input("area-toggle", "value"),  # Input from the dropdown for chart type
       
    ],
    prevent_initial_call=True
)
def togle_area_enabled(area_toggle):
    if len(area_toggle)>0:
        board.toggle()
        summary_data = board.summarize()
        fig = create_figure(
            board.window,
            x_col="date",
            y_col=board.chart_type,
            title="Leaderboard Data",
            x_label="Date",
            y_label="Profit Cumulative"
        )

        # Prepare the table data using the helper function
        summary_table_data = prepare_table_data(summary_data)
        return fig, summary_table_data
    else:
        board.toggle()
        summary_data = board.summarize()
        fig = create_figure(
            board.exclusions_df,
            x_col="date",
            y_col=board.chart_type,
            title="Leaderboard Data",
            x_label="Date",
            y_label="Profit Cumulative"
        )
        fig.update_layout(
            xaxis=dict(
                range=[board.window_start, board.window_end]  # Set the x-axis range
            )
        )
        # Prepare the table data using the helper function
        summary_table_data = prepare_table_data(summary_data)
        return fig, summary_table_data

@app.callback(
    [
        Output("graph", "figure",allow_duplicate=True),
        Output("metric_table", "data",allow_duplicate=True),
    ],
    [
        Input("chart-type-dropdown", "value"),  # Input from the dropdown for chart type
    ],
    prevent_initial_call=True
)
def update_dropdown(chart_type):
    """
    Update the chart and table based on the current data in the leaderboard.
    """
    board.chart_type  = chart_type
    original_data = board.original
    summary_data = board.summarize()

    # Create figure based on selected chart type and corresponding column
    fig = create_figure(
        original_data,
        x_col="date",
        y_col= board.chart_type,
        title="Leaderboard Data",
        x_label="Date",
        y_label="Profit Cumulative"
    )
    

    # Prepare table data from the summary
    summary_table_data = prepare_table_data(summary_data)

    # Return the updated chart and table data
    return fig, summary_table_data

@app.callback(
    [
        Output("graph", "figure"),
        Output("metric_table", "data"),
    ],
    [Input("header_title", "children"),
    ]
)
def update_chart_and_table(header_title):
    """
    Update the chart and table based on the current data in the leaderboard.
    """
    # Fetch the data and summary from the board
    exclusions_data = board.exclusions_df
    summary_data = board.summarize()

    # Generate the chart using the helper function
    fig = create_figure(
        exclusions_data,
        x_col="date",
        y_col=board.chart_type,
        title="Leaderboard Data",
        x_label="Date",
        y_label="Profit Cumulative"
    )

    # Prepare the table data using the helper function
    summary_table_data = prepare_table_data(summary_data)

    # Return the chart and the table data
    return fig, summary_table_data

# Callback to toggle visibility of the slider container
@app.callback(
    Output("slider-container", "style"),
    Input("date-range-checklist", "value")
)
def toggle_slider_visibility(selected_values):
    if "date_range_enable" in selected_values:
        return {"display": "block"}  # Show slider
    return {"display": "none"}  # Hide slider

# Callback
@app.callback(
    [
         Output("graph", "figure", allow_duplicate=True),
        Output("metric_table", "data", allow_duplicate=True),
        Output("date-range-checklist", "value")
    ],
    [
        Input("exclude-button", "n_clicks"),
        Input("reset-button", "n_clicks"),
    ],
    [
        State("date-picker-range", "start_date"),
        State("date-picker-range", "end_date")
    ],
    prevent_initial_call=True
)
def handle_buttons(exclude_clicks, reset_clicks, start_date, end_date):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update, dash.no_update

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if button_id == "exclude-button":
        if start_date and end_date:
            # Create figure based on the original data
            board.exclude_region(date.fromisoformat(start_date), date.fromisoformat(end_date))
            fig = create_figure(
                board.exclusions_df,  # Use the original data (no modification)
                x_col="date",
                y_col=board.chart_type,
                title="Leaderboard Data with Excluded Range",
                x_label="Date",
                y_label="Profit Cumulative",
            )
            fig.add_shape(
                    type="rect",
                    x0=start_date,  # Ensure format matches x-axis
                    x1=end_date,
                    y0=0,
                    y1=1,  # Full height of the plot (spanning the entire y-axis range)
                    xref="x",
                    yref="paper",  # Use paper ref for vertical span (not affected by data)
                    fillcolor="rgba(128, 128, 128, 0.3)",  # Light gray
                    layer="above",  # Ensure the exclusion area is above the lines, but not affecting the data itself
                    line=dict(width=0)  # No border for the shaded area
                )
            

            # Prepare table data from the summary
            summary_data = board.summarize()
            summary_table_data = prepare_table_data(summary_data)

            return fig, summary_table_data, ["date_range_enable"]

        else:
            return dash.no_update, dash.no_update, dash.no_update  # If no date range is selected, do nothing

    elif button_id == "reset-button":
        board.exclusions_df = board.original
        fig = create_figure(
            board.exclusions_df,  # Use original data (no exclusions)
            x_col="date",
            y_col=board.chart_type,
            title="Leaderboard Data",
            x_label="Date",
            y_label="Profit Cumulative",
        )

        summary_data = board.summarize()
        summary_table_data = prepare_table_data(summary_data)

        return fig, summary_table_data, []

    return dash.no_update, dash.no_update, dash.no_update

@app.callback(
    Output("download-dataframe-csv", "data"),
    [Input("download-button", "n_clicks"),
     Input("download-dropdown", "value")
     ]
)
def download_excel(n_clicks, dropdown_value):

    if n_clicks>0 and dropdown_value != None:
        if dropdown_value == 'window_data':
            table_data= board.window
        elif dropdown_value == 'exclusion_data':
            table_data = board.exclusions_df
        elif dropdown_value == 'original_data':
            table_data == board.original
        # Convert DataFrame to CSV
        csv_string = table_data.write_csv()
        # Encode the CSV string as a downloadable base64 string
        b64 = base64.b64encode(csv_string.encode()).decode()
        # Return the download data
        return dict(content=b64, filename="trading_data.csv")
    else:
        return dash.no_update




if __name__ == "__main__":
    app.run_server(debug=False, host= "0.0.0.0", port=8000)


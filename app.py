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

    if data is not None and not data.is_empty():
        for group in data[group_col].unique():
            filtered_data = data.filter(pl.col(group_col) == group)

            # Sort data by date
            filtered_data = filtered_data.sort(x_col)

            # Calculate cumulative profit
            filtered_data = filtered_data.with_columns(
                pl.col(y_col).cum_sum().alias("cumulative_profit")
            )

            # Add trace for each policy
            fig.add_trace(go.Scatter(
                x=filtered_data[x_col].to_list(),
                y=filtered_data["cumulative_profit"].to_list(),
                mode="lines",
                name=group
            ))

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
                                placeholder="Select data type",
                                style={"width": "200px"}
                            ),

                            dbc.Checklist(
                                options=[{"label": "Enable Area", "value": "enable"}],
                                value=[],  # Initially unchecked
                                id="area-toggle",
                                switch=True,
                                style={"marginLeft": "10px"}
                            ),
                            html.Button(
                                "Reset Chart",
                                id="reset-chart-button",
                                style={
                                    "marginLeft": "10px",
                                    "backgroundColor": "#4682B4",
                                    "border": "none",
                                    "color": "white",
                                    "padding": "10px",
                                    "borderRadius": "5px",
                                    "cursor": "pointer"
                                }
                            )
                        ]
                    ),
                    # Chart container and the content for selected tab
                    html.Div(
                        id="chart-container",
                        style={"marginBottom": "20px"}
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
                                id="model-dropdown",
                                options=[
                                    {"label": "PJMvirts Captain Hindsight", "value": "Captain Hindsight"},
                                    {"label": "PJMvirts Pricetaker Short", "value": "Pricetaker Short"},
                                    {"label": "PJMvirts Pricetaker Long", "value": "Pricetaker Long"}
                                ],
                                placeholder="Select a model",
                                style={"flex": "1"}
                            ),
                            html.Button(
                                html.I(className="fas fa-download", style={"fontSize": "24px", "color": "white"}),
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
                                    {"name": "Policy", "id": "policy"},
                                    {"name": "PnL", "id": "PnL"},
                                    {"name": "Per MWh", "id": "per MWh"},
                                    {"name": "Win %", "id": "win %"}
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
    [
        Output("chart-container", "children",allow_duplicate=True),
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
    
    original_data = board.original
    summary_data = board.summarize()

    # Create figure based on selected chart type and corresponding column
    fig = create_figure(
        original_data,
        x_col="date",
        y_col= chart_type,
        title="Leaderboard Data",
        x_label="Date",
        y_label="Profit Cumulative"
    )
    

    # Prepare table data from the summary
    summary_table_data = prepare_table_data(summary_data)

    # Return the updated chart and table data
    return dcc.Graph(figure=fig), summary_table_data

@app.callback(
    [
        Output("chart-container", "children"),
        Output("metric_table", "data"),
    ],
    [Input("header_title", "children")]
)
def update_chart_and_table(header_title):
    """
    Update the chart and table based on the current data in the leaderboard.
    """
    # Fetch the data and summary from the board
    original_data = board.original
    summary_data = board.summarize()

    # Generate the chart using the helper function
    fig = create_figure(
        original_data,
        x_col="date",
        y_col="profit_total",
        title="Leaderboard Data",
        x_label="Date",
        y_label="Profit Cumulative"
    )

    # Prepare the table data using the helper function
    summary_table_data = prepare_table_data(summary_data)

    # Return the chart and the table data
    return dcc.Graph(figure=fig), summary_table_data

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
        Output("chart-container", "children", allow_duplicate=True), 
        Output("metric_table", "data", allow_duplicate=True),
        Output("date-range-checklist", "value")
        
    ],
    [
        Input("exclude-button", "n_clicks"),
        Input("reset-button", "n_clicks"),
        Input("chart-type-dropdown", "value"),
    ],
    [
        State("date-picker-range", "start_date"),
        State("date-picker-range", "end_date")
    ],
    prevent_initial_call=True
)
def handle_buttons(exclude_clicks, reset_clicks, start_date, end_date,chart_type):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update , dash.no_update

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]

    if button_id == "exclude-button":
        if start_date and end_date:
            # Exclude region in the board
            print(date.fromisoformat(start_date), date.fromisoformat(end_date))
            board.exclude_region(date.fromisoformat(start_date), date.fromisoformat(end_date))
            exclusions_data = board.exclusions_df
            summary_data = board.summarize()
            print(summary_data)
            # Create chart and table
            fig = create_figure(
                exclusions_data, x_col="date", y_col=chart_type,
                title="Excluded Data", x_label="Date", y_label="Profit Cumulative"
            )
            summary_table_data = prepare_table_data(summary_data)

            return dcc.Graph(figure=fig), summary_table_data , ["date_range_enable"]

        else:
            return dcc.Graph(), [],[]  # Return empty if no valid range

    elif button_id == "reset-button":
        # Reset the board
        original_data = board.original
        board.window = board.original
        board.exclusions_df = board.original
        summary_data = board.summarize()

        # Create chart and table
        fig = create_figure(
            original_data, x_col="date", y_col=chart_type,
            title="Leaderboard Data", x_label="Date", y_label="Profit Cumulative"
        )
        summary_table_data = prepare_table_data(summary_data)

        return dcc.Graph(figure=fig), summary_table_data ,[]

    return None, [] , []

# Callback to download data as CSV
@app.callback(
    Output("download-dataframe-csv", "data"),
    [Input("download-button", "n_clicks")],
    [State("metric_table", "data")]
)
def download_csv(n_clicks, table_data):
    if n_clicks:
        # Convert the table data into a pandas DataFrame
        df = pd.DataFrame(table_data)

        # Convert DataFrame to CSV
        csv_string = df.to_csv(index=False, encoding='utf-8')

        # Encode the CSV string as a downloadable base64 string
        b64 = base64.b64encode(csv_string.encode()).decode()

        # Return the download data
        return dict(content=b64, filename="trading_data.csv")
    return dash.no_update

if __name__ == "__main__":
    app.run_server(debug=True, port=8050)


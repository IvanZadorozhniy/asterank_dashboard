from re import template
from dash import Dash, html, dcc, Input, Output, State, dash_table
import pandas as pd
import plotly.express as px
import requests
import os.path
import logging
import dash_bootstrap_components as dbc
import numpy as np

import plotly.graph_objects as go

logging.basicConfig(level=logging.INFO)

query = "{}"
limit = 5000
data_file_path = "./data.parquet"
api_link = f"http://asterank.com/api/kepler?query={query}&limit={limit}"


def get_data():
    if os.path.exists(data_file_path):
        logging.info("There is a data file locally")
        df = pd.read_parquet(data_file_path)
    else:
        logging.info("There is no a data file locally. \n Use API to get data")
        try:
            response = requests.get(api_link)
        except:
            logging.info(
                "Internet connection may not working or Server with Api doesn't response")
            exit()
        df = pd.json_normalize(response.json())
        df.to_parquet("data.parquet")
    return df


df = get_data()
df = df[df['PER'] > 0]

''' FEATURE ENGINEERING '''

bins = [0, 0.8, 1.2, 100]
names = ['Small', 'Similar', 'Bigger']
df['StarSize'] = pd.cut(df['RSTAR'], bins, labels=names)
options = [{"label": k, "value": k} for k in names]

''' TEMPERATURE '''
tp_bins = [0, 200, 400, 500, 5000]
tp_labels = ['low', 'optimal', 'hight', 'extreme']
df['Temperature'] = pd.cut(df['TPLANET'], tp_bins, labels=tp_labels)

''' SIZE '''
rp_bins = [0, 0.5, 2, 4, 100]
rp_labels = ['low', 'optimal', 'hight', 'extreme']
df['Gravity'] = pd.cut(df['RPLANET'], rp_bins, labels=rp_labels)

''' ESTIMATE_STATUS '''
df['Status'] = np.where(
    (df['Temperature'] == 'optimal') & (df['Gravity'] == 'optimal'),
    'Promising', None
)

df.loc[:, 'Status'] = np.where(
    (df['Temperature'] == 'optimal') & (df['Gravity'].isin(['low', 'hight'])),
    'Challenging', df['Status']
)

df.loc[:, 'Status'] = np.where(
    (df['Gravity'] == 'optimal') & (df['Temperature'].isin(['low', 'hight'])),
    'Challenging', df['Status']
)

df['Status'] = df["Status"].fillna("Extreme")

""" Relative Distatnce"""
df.loc[:,"Relative_distance"] = df["A"] / df["RSTAR"]

''' GLOBAL  DESIGN SETTINGS '''
CHARTS_TEMPLATE = go.layout.Template(
 layout = {
     "legend" : {
         "orientation": "h",
         "title_text": "",
         "x": 0,
         "y": 1.2,
         "title": ""
     },
     "font" : {
         "family" : "Century Gothic"
     }
 }   
)

COLORS_STATUS_VALUES = ["#334252", "#0000A1", "#C00000"]
# print(df.groupby("Status")["ROW"].count())
''' COMPONENTS '''
star_size_selector = dcc.Dropdown(
    id='star-selector',
    options=options,
    value=[],
    multi=True
)

rplanet_selector = dcc.RangeSlider(
    id="range-slider",
    min=min(df["RPLANET"]),
    max=max(df["RPLANET"]),
    marks={x: f"{x}" for x in range(
        int(min(df["RPLANET"])), int(max(df["RPLANET"])), 10)},
    step=1,
    value=[min(df["RPLANET"]), max(df["RPLANET"])]
)

app = Dash(__name__, external_stylesheets=[dbc.themes.FLATLY], meta_tags=[
        {"name": "viewport", "content": "width=device-width, initial-scale=1"}
    ],)

'''TABS'''
tab1_content = [
    dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(
                            "Planet Temperature ~ Distance from the Start"),
                        html.Div(dcc.Graph(id="dist-temp-chart"))
                    ], lg=6,md=10,sm=12
                ),
                dbc.Col(
                    [
                        html.Div("Position on the Calestial Sphere"),
                        html.Div(dcc.Graph(id="calesial-splhere-graph"))
                    ],lg=6,md=10,sm=12
                )
            ],justify="center"
            
        ),
        dbc.Row(
            [
                dbc.Col([html.Div(
                            "Planet Temperature ~ Distance from the Start"),
                         html.Div(id="relative-dist-chart") ],lg=6,md=10,sm=12),
                dbc.Col([
                    html.Div(
                            "Planet Temperature ~ Distance from the Start"),
                    html.Div(id="mstar-tstar-chart")
                    ], lg=6,md=10,sm=12),
            ],justify="center"
        )
]

tab2_content = [
    dbc.Row(
        [
            dbc.Col(html.Div(id="data-table", style={"maxWith": "90%"}), lg=11,md=11,sm=11)
        ], justify="center"
    )
    
]
table_header = [
    html.Thead(html.Tr([html.Th("Field Name"), html.Th("Details")]))
]
explaitor = {
"KOI": "Object of Interest number",
      "A":"Semi-major axis (AU)",
      "DEC":"Planetary radius (Earth radii)",
      "RSTAR":"Stellar radius (Sol radii)",
      "TSTAR":"Effective temperature of host star as reported in KIC (k)",
      "KMAG":"Kepler magnitude (kmag)",
      "TPLANET":"Equilibrium temperature of planet, per Borucki et al. (k)",
      "T0":"Time of transit center (BJD-2454900)",
      "UT0":"Uncertainty in time of transit center (+-jd)",
      "PER":"Uncertainty in time of transit center (+-jd)",
      "RA":"Period (days)",
      "UPER":"Uncertainty in period (+-days)",
      "RPLANET":"Declination (@J200)",
      "MSTAR":"Right ascension (@J200)",
      "ROW":"Derived stellar mass (msol)"
}

table_rows = [html.Tr([html.Td(i), html.Td(explaitor[i])]) for i in explaitor.keys()]

table_body = [html.Tbody(table_rows)]
table = dbc.Table(table_header + table_body, bordered= True)
text_link = "Data are sourced from Keplar API via asterlink.com"
tab3_content = [
    dbc.Row(
        [
            dbc.Col(
                [
                    html.Div(html.A(text_link, href="https://www.asterank.com/kepler"))
                ], 
            )
        ]
    ),
    dbc.Row(
        dbc.Col(html.Div(
            children=table
        ), lg=6,md=8,sm=11)
    ,justify="center")
]
''' LAYOUT '''

app.layout = html.Div(
    children=[
        dbc.Row(
            dbc.Col(
                [
                    html.H1("Planet DashBoard Pet-Project")
                ]
            )
        ),

        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(className="selector_wrapper", children=
                            [
                                html.Div("Selector radius planet"),
                                html.Div(rplanet_selector)
                            ]
                            )
                    ], md=6, sm=12
                ), 
                dbc.Col(
                    html.Div(className="selector_wrapper", children=
                     [html.Div("Star size filter"),
                    html.Div(star_size_selector)]), md=4,sm=12,
                     
                ),
                dbc.Col(
                    html.Div(dbc.Button("Apply", id="submit-value-btn",
                                   n_clicks=0,)), md=2,sm=12, align="center"
                    
                )
            ],
            justify="center"
        ),
        dbc.Tabs(
            [
                dbc.Tab(tab1_content, label="Charts",),
                dbc.Tab(tab2_content, label="Data",),
                dbc.Tab(tab3_content, label="Info",)
               
            ],
        )
        

        
    ],
)

''' CALLBACK '''


@app.callback(
    [Output(component_id="dist-temp-chart", component_property="figure"),
    Output(component_id="calesial-splhere-graph", component_property="figure"),
    Output(component_id="relative-dist-chart", component_property="children"),
    Output(component_id="mstar-tstar-chart", component_property="children"),
    Output(component_id="data-table", component_property="children")],

    Input(component_id="submit-value-btn", component_property="n_clicks"),
    [
        State(component_id="range-slider", component_property="value"),
        State(component_id="star-selector", component_property="value")
    ]
)
def update_dist_temp_chart(n, radius_range, star_size):
    if not star_size:
        chart_data = df[(df["RPLANET"] >= radius_range[0]) &
                        (df["RPLANET"] <= radius_range[1])]
    else:
        chart_data = df[(df["RPLANET"] >= radius_range[0]) & (
            df["RPLANET"] <= radius_range[1]) & (df['StarSize'].isin(star_size))]

    fig = px.scatter(
        data_frame=chart_data,
        x="RPLANET",
        y="A",
        color="StarSize"
    )
    fig = fig.update_layout(template=CHARTS_TEMPLATE)
    fig = fig.update_layout(legend_title_text = "")
    fig2 = px.scatter(
        data_frame=chart_data,
        x="RA",
        y="DEC",
        color="Status",
        size="RPLANET",
        color_discrete_sequence = COLORS_STATUS_VALUES
    )
    fig2 = fig2.update_layout(template=CHARTS_TEMPLATE)
    fig2 = fig2.update_layout(legend_title_text = "")
    relative_distance_chart = px.histogram(chart_data, x="Relative_distance",
                                           color="Status",
                                           marginal="violin", barmode="overlay")
    
    relative_distance_chart.add_vline(x=1, annotation_text="Earth", line_dash="dot")
    relative_distance_chart = relative_distance_chart.update_layout(template=CHARTS_TEMPLATE)
    relative_distance_chart = relative_distance_chart.update_layout(legend_title_text = "")
    html_relative_distance = [
        html.Div("Relavice Distance"),
        dcc.Graph(figure=relative_distance_chart)
    ]
    
    mass_star_chart = px.scatter(chart_data, x="MSTAR", y="TSTAR", size="RPLANET", color="Status")
    mass_star_chart = mass_star_chart.update_layout(template=CHARTS_TEMPLATE)
    mass_star_chart = mass_star_chart.update_layout(legend_title_text = "")
    html_mass_star = [
        html.Div("Star Mass ~ Star Temperature"),
        dcc.Graph(figure=mass_star_chart)              
    ]
    raw_data = chart_data.drop(columns=['Relative_distance', 'StarSize', "Temperature", "Gravity", "Status"])
    raw_data_table =  dash_table.DataTable(data=raw_data.to_dict('records'), columns=[{"name":i, "id":i} for i in raw_data.columns],
                                           page_size=40, style_table={
        'overflowY': 'scroll',
        'overflowX': 'scroll',
        "height": "500px"
        
    }
    )
    html_data_table = [
        html.P("Raw_Data"),
        raw_data_table
    ]
    return [fig, fig2, html_relative_distance, html_mass_star, html_data_table]


if __name__ == '__main__':

    # app.run_server(debug=True)
    app.run_server(host='0.0.0.0', port=8000)

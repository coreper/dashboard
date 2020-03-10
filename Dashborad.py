import dash
import dash_auth
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import pandas as pd
import base64
import numpy as np
import os
import time
from datetime import datetime, timedelta


os.environ['TZ'] = 'right/UTC' # TAI scale with 1970-01-01 00:00:10 (TAI) epoch
time.tzset() # Unix

def GPS2current(GPS_time=301773079421553.0):
    gps_timestamp = GPS_time * 0.000001 # input
    gps_epoch_as_gps = datetime(2004, 1, 1)
    # by definition
    gps_time_as_gps = gps_epoch_as_gps + timedelta(seconds=gps_timestamp)
    gps_time_as_tai = gps_time_as_gps + timedelta(seconds=19) # constant offset
    tai_epoch_as_tai = datetime(1970, 1, 1, 0, 0, 10)
    # by definition
    tai_timestamp = (gps_time_as_tai - tai_epoch_as_tai).total_seconds()
    current_time = datetime.utcfromtimestamp(tai_timestamp)
    return current_time

def encode_image(image_file):
    encoded = base64.b64encode(open(image_file, 'rb').read())
    return 'data:image/png;base64,{}'.format(encoded.decode())


df = pd.read_csv('./demo.csv')
filtered_df = pd.DataFrame()
year = []
month = []
day = []
hour = []
for i in range(df.shape[0]):
    time_ = GPS2current(df['Time'].iloc[i])
    year.append(time_.year)
    month.append(time_.month)
    day.append(time_.day)
    hour.append(time_.hour)
df['year'] = year
df['month'] = month
df['day'] = day
df['hour'] = hour
max_date_ = GPS2current(df['Time'].max())
min_date_ = GPS2current(df['Time'].min())

app = dash.Dash()
mapbox_access_token = 'pk.eyJ1IjoiY29yZXBlciIsImEiOiJjazR5OWU4eWkwOWVkM21sZDN6NmoxNWU4In0.Sxn_e0AKN-m0s6GVl1KugA'

trajectory_options = []
for instance in df['Instance'].unique():
    trajectory_options.append({'label': 'Trip ' + str(instance), 'value': instance})


app.layout = html.Div([
    html.H2(
        children='DENSO Driving Behavior Project',
        style=dict(
            textAlign='center',
            color='red',
        )
    ),

    html.P(
        children = """
            DENSO driving behavior data analytic platform is to analyze the realtime intersection
            traffic, including realtime speed prediction, aggressiveness prediction, driving behavior 
            interpretation and driving behavior prediction.
        """,
        style = dict(
            fontFamily = 'helvetica',
            fontSize = 15,
            fontStyle = 'italic',
            fontWeight = 'bold'
        )
    ),

    # html.Img(
    #     src=encode_image('./densoimg.png'),
    #     style=dict(
    #         height='220px',
    #     )
    # ),

    html.Embed(src="https://www.youtube.com/embed/1EiC9bvVGnk",
               style=dict(width='490px',
                          height='280px')
               ),

    html.P(
        children = """
            Select (single) day and (multiple) hours.
        """,
        style = dict(
            fontFamily = 'helvetica',
            fontSize = 15,
            fontStyle = 'italic',
            # fontWeight = 'bold'
        )
    ),

    html.Div(
        dcc.DatePickerSingle(
            id='date',
            date=str(max_date_.date()),
            display_format='MMM Do, YY',
            max_date_allowed = str(max_date_.date()),
            min_date_allowed = str(min_date_.date()),
            style = dict(
                fontFamily = 'helvetica',
                fontWeight = 'bold',
            )
        ),
        style=dict(
            float='left',
            display='inline-block',
            alignItems ='center',
        ),
    ),

    html.Div(
        dcc.Dropdown(
            id='time',
            options=[
                {
                    "label": str(n) + ":00",
                    "value": str(n),
                }
                for n in range(24)
            ],
            value=['13:00', '13'],
            multi=True,
            clearable=True,
            placeholder="Empty means selecting all",
            style=dict(
                height = '48px',
                fontFamily = 'helvetica',
            )
        ),
        style=dict(
            width='72.7%',
            height = '48px',
            # float='right',
            display='inline-block',
            alignItems ='center',
        )
    ),

    html.Div([
        dcc.Dropdown(
            id='trajectory-picker',
            multi=True,
            placeholder="Select multiple trajectories",
            style=dict(
                height='70px',
                fontFamily = 'helvetica',
            ),
        )],
        style=dict(
            height = '70px',
            # width = '30%',
            # display = 'inline-block',
            alignItems ='center',
        )),

    dcc.Graph(id='map_trajectory'),
    dcc.Graph(id='speed_fig'),

    html.Div(
            id='interpretation',
        ),
    ],
    style=dict(
        # fontSize='20'
    )
)


@app.callback(Output('trajectory-picker', 'options'),
              [Input('date', 'date'),
               Input('time', 'value')])
def update_date_dropdown(date, time):
    select_date = datetime.strptime(date[:10], '%Y-%m-%d')
    global filtered_df
    filtered_df = df[
        (df['year'] == select_date.year) & (df['month'] == select_date.month) & (df['day'] == select_date.day)]

    if len(time) == 0:
        filtered_df = filtered_df
    elif len(time[0])>2:
        filtered_df = filtered_df[filtered_df['hour'] == int(time[1])]
    else:
        time = [int(i) for i in time]
        filtered_df = filtered_df[filtered_df['hour'].isin(time)]

    trajectory_options = []
    for instance in filtered_df['Instance'].unique():
        trajectory_options.append({'label': 'Trip ' + str(instance), 'value': instance})
    return trajectory_options


@app.callback(Output('map_trajectory', 'figure'),
              [Input('trajectory-picker', 'value')])
def update_map(selected_traj):
    data = []
    filtered_df_ = filtered_df[filtered_df['Instance'].isin(selected_traj)]
    for instance_df in filtered_df_.groupby('Instance'):
        instance_df = instance_df[1]
        traj_id = instance_df['Instance'].unique()[0]

        trace = go.Scattermapbox(
                    lat=instance_df['Lat'],
                    lon=instance_df['Long'],
                    mode='markers',
                    name=str(traj_id),
                    marker=dict(
                        size=10,
                        colorscale='Viridis',
                        opacity=0.5,
                    ),
                )
        data.append(trace)

    layout = go.Layout(
        autosize=True,
        hovermode='closest',
        mapbox_style='light',
        height=500,
        margin=go.layout.Margin(
            l=0,
            r=0,
            b=30,
            t=10,
            pad=4
        ),
        legend=dict(
            x=0,
            y=1,
            traceorder="normal",
            font=dict(
                family="sans-serif",
                size=12,
                color="black"
            ),
            bordercolor="LightBlue",
            borderwidth=1
        ),
        mapbox=dict(
            accesstoken=mapbox_access_token,
            bearing=0,
            center=go.layout.mapbox.Center(
                lat=42.294876,
                lon=-83.719063,
                    ),
            pitch=0,
            zoom=17.5,)
    )
    fig = dict(data=data, layout=layout)
    return fig


@app.callback(Output('speed_fig', 'figure'),
              [Input('trajectory-picker', 'value')])
def update_figure(selected_traj):
    data = []
    filtered_df_ = filtered_df[filtered_df['Instance'].isin(selected_traj)]
    for instance_df in filtered_df_.groupby('Instance'):
        instance_df = instance_df[1]
        traj_id = instance_df['Instance'].unique()[0]

        trace = go.Scatter(
                    x=instance_df['CP_dist'],
                    y=instance_df['Speed'],
                    mode='lines+markers',
                    name=str(traj_id),
                    marker=dict(
                        size=6,
                        colorscale='Viridis',
                        color=instance_df['clusters'],
                        opacity=0.5,

                    ),
                    line=dict(
                        width=1,
                        color='black',
                        dash='dot'
                    ),
                )
        data.append(trace)

    layout = go.Layout(
        title='Vehicle speed vs. distance to stop line',
        xaxis = dict(
            title='Distance to stop line',
        ),
        yaxis=dict(
            title = 'Vehicle speed',
        ),
        autosize=True,
        hovermode='closest',
        mapbox_style='light',
        height=300,
        font=dict(
            family='helvetica',
            size=10,
        ),
        margin=go.layout.Margin(
            l=0,
            r=0,
            b=30,
            t=30,
            pad=4
        ),
        legend=dict(
            x=0.77,
            y=0,
            traceorder="normal",
            font=dict(
                family="sans-serif",
                size=12,
                color="black"
            ),
            bordercolor="LightBlue",
            borderwidth=1
        ),
    )
    fig = dict(data=data, layout=layout)
    return fig

@app.callback(Output('interpretation', 'children'),
              [Input('trajectory-picker', 'value')])
def update_description(selected_traj):
    bad_chars = ['[', ']', "'"]
    filtered_df_ = filtered_df[filtered_df['Instance'].isin(selected_traj)]
    descrips = []

    for instance_df in filtered_df_.groupby('Instance'):
        instance_df = instance_df[1]
        # traj_name = '#### Trajectory ' + str(instance_df['Instance'].unique()[0])
        traj_name = 'Trajectory ' + str(instance_df['Instance'].unique()[0])
        descrips.append(html.P(traj_name,
                                style=dict(color = 'black',
                                           fontStyle = 'italic',
                                           fontSize = 14,
                                           fontFamily = 'helvetica',
                                           fontWeight = 'bold'
                                           )))

        traj_desc = instance_df['interp'].iloc[0]
        traj_desc = ''.join(i for i in traj_desc if not i in bad_chars)
        descrips_ = traj_desc.split(',')



        for i in range(len(descrips_)):
            cluster_num = 'Cluster ' + str(i + 1) + ': ' if i == 0 \
                else 'Cluster ' + str(i + 1) + ':'
            descrips.append(html.P(cluster_num + descrips_[i],
                                   style=dict(color='black',
                                              # fontStyle='italic',
                                              fontSize=12,
                                              fontFamily='helvetica',
                                              )))

    return descrips

if __name__ == '__main__':
    app.run_server(debug=True, host='192.168.1.76', port = 8080)
# ----------------------------------------------------------
# author:	PKN
# filename:	showSensorData.py
# info:		Python script to get data from serial
# 			connected datalogger (OTT-radar) and modbus
# 			(NKE - MoSens UV sensor) and display collected
#			data in a graph.
# ----------------------------------------------------------

import serial, datetime, time, re, random
from ctypes import *
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from dash import Dash, dcc, html, Input, Output
import minimalmodbus

# SETTINGS
use_test_data = True
debugMode_data = False
debugMode_NKE = False
debugMode_plot = False
OTT_port = 'COM10' #port name
OTT_offset = 40.00 # offset in cm
NKE_port = 'COM9' #port name
NKE_Address = 128 #slave address (in decimal)

pd.options.plotting.backend = 'plotly'
plotly_template = 'plotly_white' # "plotly", "plotly_white", "plotly_dark", "ggplot2", "seaborn", "simple_white", "none"
max_plotdata = 50 # max measurements to show 
refreshrate = 5000, # in milliseconds
fig_height = 600
fig_width = 800
scale_distance = [-20, 20]
scale_Uv = [0, 1.5]
scale_temperature = [0, 30]
scale_Ec = [0, 6]

# INIT
plotdata = [[datetime.datetime.now(),0.00,0.00,0.00,00.00]] # create startpoint for plot

# Modbus
if use_test_data == False:
    instrument = minimalmodbus.Instrument(NKE_port, NKE_Address)
    instrument.serial.baudrate = 9600
    instrument.serial.bytesize = 8
    instrument.serial.parity   = serial.PARITY_EVEN
    instrument.serial.stopbits = 1
    instrument.serial.timeout  = 1        # seconds
    instrument.mode = minimalmodbus.MODE_RTU   # rtu or ascii mode
    instrument.debug = debugMode_NKE
    instrument.BYTEORDER_BIG = 0

class dataObject():
    def __init__(self):
        self.datetime = datetime.datetime.now()
        self.distance = (get_distance() - OTT_offset)
        gt_data = get_NKE_data()
        self.temperature = recalc_output(gt_data[4],gt_data[5])
        self.Ec = recalc_output(gt_data[2],gt_data[3])
        self.Uv = recalc_output(gt_data[0],gt_data[1])

class test_dataObject():
    def __init__(self):
        self.datetime = datetime.datetime.now()
        self.distance = round(random.uniform(-20.00, 20.00),2)-OTT_offset
        self.temperature = round(random.uniform(12.00, 23.00),2)
        self.Ec = round(random.uniform(0.00, 5.00),2)
        self.Uv = round(random.randint(0, 1))

# minimalmodbus output is based on 2 bytes, NKE output = 4 bytes
# recalculate output to show correct measurement values
def recalc_output(n,m): 
    p=('{0:x}'.format(n))
    q=('{0:x}'.format(m))
    r=p+q
    if len(r) == 8:
        i = int(r,16)
        cp = pointer(c_int(i))
        fp = cast(cp, POINTER(c_float))
        if debugMode_data:
            print(f'converted value= {fp.contents.value}' )
        return fp.contents.value
    else:
        return(0.00)

def get_distance(): # Distance from Radar in cm.
    ser = serial.Serial(OTT_port, 9600, 8, 'N', 1, timeout=1)
    P1 = 9999
    while P1 != 0 and P1 > 9999:
        output = ser.readline()
        output = output.decode('ascii')
        regresult = re.split(';', output)
        while regresult != [''] and regresult != ['\x00']:
            P1 = float(regresult[3])
            if P1 == 9999999:
                P1 = 0
            else:
                P1 = P1
            if debugMode_data:
                print(f'P1: {P1}')
            return P1
        
def get_NKE_data():
    try:
        # Arguments - (register start address, number of registers to read, function code) 
        NKE_data = instrument.read_registers(256,6,4)
        if debugMode_data:
            print(f'NKE_data: {NKE_data}')
        return NKE_data
    except IOError:
        print('Failed to read from instrument')  

app = Dash(__name__)
app.layout = html.Div([
    html.Img(src=app.get_asset_url('logo.svg')),
    html.H1(
        children='Sensor Data',
        style={
            'text-indent': '10px',
            'textAlign': 'left',
            'color': 'white',
            'background-color': 'rgb(32, 85, 128)'
        },
    ),
    
    html.Div([
        dcc.Dropdown(
            ["plotly", "plotly_white", "plotly_dark", "ggplot2", "seaborn", "simple_white"], 'plotly_white',
            id='template',
            style=dict(
                width='120px',
                display='inline-block',
            ),
        ),
        dcc.Dropdown(
            id='kind_of_data', 
                options=[
                    {'label': 'Sensor Data', 'value': 'Sensor'},
                    {'label': 'Demo Data', 'value': 'Demo'}
                ], value= 'Sensor',
            style=dict(
                width='120px',
                display='inline-block',
            ),
        )
    ],
        style=dict(display='flex')
    ),

    html.Br(),
    html.Div([
        " OTT-radar offset: ",
        dcc.Input(id='offset_input', value=OTT_offset, type='number',
            style=dict(
            width='40px',
            display='inline-block',
            verticalAlign="middle",
            ),
        ),
        " Port OTT-radar:  ",
        dcc.Input(id='OTT_input', value=OTT_port, type='text', 
            style=dict(
            width='80px',
            display='inline-block',
            ),
        ),
        " Port NKE Mosens Uv: ",
        dcc.Input(id='NKE_input', value=NKE_port, type='text',
            style=dict(
            width='80px',
            display='inline-block',
            verticalAlign="middle",
            ),
        ),
    ]),

    dcc.Interval(
    id='interval-component',
    interval=refreshrate ,
    n_intervals=0
    ),
    dcc.Graph(id='graph')
])

# Define callback to update graph
@app.callback(
    Output('graph', 'figure'),
    Input('interval-component', 'n_intervals'),
    Input(component_id='template', component_property='value'),
    Input(component_id='offset_input', component_property='value'),
    Input(component_id='OTT_input', component_property='value'),
    Input(component_id='NKE_input', component_property='value'),
    Input(component_id='kind_of_data', component_property='value')
)
def update_line_chart(sensorData, template, offset_input, OTT_input, NKE_input, kind_of_data):
    plotly_template = template
    OTT_offset = offset_input
    OTT_port = OTT_input
    NKE_port = NKE_input
    if kind_of_data == "Sensor":
        use_test_data = False
    else:
        use_test_data = True
    if use_test_data == True:
        sensordata =  test_dataObject()
    else:
        sensordata = dataObject()
    newdata = [sensordata.datetime,sensordata.distance,sensordata.temperature,sensordata.Ec,sensordata.Uv]
    if len(plotdata) < max_plotdata:
        plotdata.append(newdata)
    else:
        plotdata.pop(0) #remove oldest item from array
        plotdata.append(newdata)
    
    fig = make_subplots(rows=2, cols=2, subplot_titles=('OTT-radar','NKE sensor - Uv','NKE sensor - temperatuur','NKE sensor - Ec')) #create subplots
    df = pd.DataFrame(plotdata, columns = ('time','distance','temperature','Ec','Uv'))
    fig.append_trace(go.Scatter(x=df['time'], y=df['distance'], name='waterhoogte'),row=1,col=1)
    fig.append_trace(go.Scatter(x=df['time'], y=df['Uv'], name='status Uv LED'),row=1,col=2)
    fig.append_trace(go.Scatter(x=df['time'], y=df['temperature'], name='water temperatuur'),row=2,col=1)
    fig.append_trace(go.Scatter(x=df['time'], y=df['Ec'], name='water geleidbaarheid'),row=2,col=2)
    # Update xaxis properties
    fig.update_xaxes(title_text="tijd", row=1, col=1)
    fig.update_xaxes(title_text="tijd", row=1, col=2)
    fig.update_xaxes(title_text="tijd", row=2, col=1)
    fig.update_xaxes(title_text="tijd", row=2, col=2)
    
    # Update yaxis properties
    fig.update_yaxes(title_text="cm (NAP)", range=scale_distance, row=1, col=1)
    fig.update_yaxes(title_text="status", range=scale_Uv, row=1, col=2)
    fig.update_yaxes(title_text="\N{DEGREE SIGN}C", range=scale_temperature,row=2, col=1)
    fig.update_yaxes(title_text="mS/cm", range=scale_Ec, row=2, col=2)
    
    fig.update_layout(height=fig_height,width=fig_width, template=plotly_template)
    
    return fig     

app.run_server(port = 8069, dev_tools_ui=True, debug=debugMode_plot,
              dev_tools_hot_reload =True, threaded=True)


# ----------------------------------------------------------
# author:	PKN
# filename:	showSensorData.py
# info:		Python script to get data from serial
# 			connected datalogger (OTT-radar) and modbus
# 			(NKE - MoSens UV sensor) and display collected
#			data in a graph.
# ----------------------------------------------------------

import serial, datetime, time, re, random
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, dcc, html, Input, Output
import minimalmodbus

# SETTINGS
use_test_data = True
debugMode_data = False
debugMode_NKE = False
debugMode_plot = False
OTT_port = '/dev/ttyUSB0' #port name
NKE_port = '/dev/ttyUSB1' #port name
NKE_Address = 128 #slave address (in decimal)

pd.options.plotting.backend = 'plotly'
plotly_template = 'plotly_dark' # "plotly", "plotly_white", "plotly_dark", "ggplot2", "seaborn", "simple_white", "none"
max_plotdata = 50 # max measurements to show 
refreshrate = 5000, # in milliseconds
plotcols = ('time','distance','temperature','Ec','Uv')
x_axis = 'time'
y_axis = ['distance','temperature','Ec','Uv']
plotdata = [[datetime.datetime.now(),0.00,0.00,0.00,00.00]] # create startpoint for plot

# Modbus
instrument = minimalmodbus.Instrument(NKE_port, NKE_Address)
instrument.serial.baudrate = 9600
instrument.serial.bytesize = 8
instrument.serial.parity   = serial.PARITY_EVEN
instrument.serial.stopbits = 1
instrument.serial.timeout  = 1        # seconds
instrument.mode = minimalmodbus.MODE_RTU   # rtu or ascii mode
instrument.debug = debugMode_NKE

class dataObject():
    def __init__(self):
        self.datetime = datetime.datetime.now()
        self.distance = get_distance()
        gt_data = get_NKE_data()
        self.temperature = gt_data[2]/1000
        self.Ec = gt_data[1]/1000
        self.Uv = gt_data[0]/1000

class test_dataObject():
    def __init__(self):
        self.datetime = datetime.datetime.now()
        self.distance = round(random.uniform(28.00, 45.00),2)
        self.temperature = round(random.uniform(12.00, 23.00),2)
        self.Ec = round(random.uniform(12.00, 23.00),2)
        self.Uv = round(random.uniform(12.00, 23.00),2)

def get_distance(): # Distance from Radar in cm.
    ser = serial.Serial(OTT_port, 9600, 8, 'N', 1, timeout=1)
    P1 = 999
    while P1 != 0 and P1 > 120:
        output = ser.readline()
        output = output.decode('ascii')
        regresult = re.split(';', output)
        while regresult != [''] and regresult != ['\x00']:
            P1 = float(regresult[3])
            if P1 == 9999999:
                P1 = 0
            else:
                P1 = P1 * 10
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
    html.H1("Sensor data"),
            dcc.Interval(
            id='interval-component',
            interval=refreshrate ,
            n_intervals=0
        ),
    dcc.Graph(id='graph'),
])

# Define callback to update graph
@app.callback(
    Output('graph', 'figure'),
    [Input('interval-component', 'n_intervals')]
)
def update_line_chart(sensorData):
   
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
    df = pd.DataFrame(plotdata, columns = plotcols)
    fig = px.line(df, x=x_axis, y=y_axis, template=plotly_template, markers=True)
    
    fig.update_layout(
    xaxis_title="tijd",
    yaxis_title="meetwaarden",
    legend_title="metingen")
    return fig     

app.run_server(port = 8069, dev_tools_ui=True, debug=debugMode_plot,
              dev_tools_hot_reload =True, threaded=True)


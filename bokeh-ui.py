from bokeh.plotting import figure
from bokeh.models import ColumnDataSource, \
    Column, \
    Button, \
    DataTable, \
    TableColumn, \
    Row, \
    Slider, \
    DatePicker, \
    TextInput, \
    CustomJS, \
    Div, \
    HoverTool, \
    GeoJSONDataSource, \
    Select
from bokeh.palettes import Viridis
from bokeh.io import curdoc
from bokeh.events import DoubleTap
import pandas as pd
import geopandas as gpd
from datetime import datetime, timedelta
import aux_functions as af
from bokeh.themes import built_in_themes
import numpy as np
import math
from itertools import cycle

street_map = gpd.read_file('shp/hold/geo_export_0a23a24b-8a75-4a43-b238-df5c9996dcf4.shp')
street_source = GeoJSONDataSource(geojson=street_map.to_json())

coordList=[]

source = ColumnDataSource(pd.DataFrame(data=dict(x=[], y=[])))
line_source = ColumnDataSource(pd.DataFrame({'latitude' : [], 'longitude' : []}))
initpop = ColumnDataSource(pd.DataFrame({'init_pop' : [10]}))
numgens = ColumnDataSource(pd.DataFrame({'num_gens' : [5]}))
date = ColumnDataSource(pd.DataFrame({'date' : [datetime.today()]}))
hour = ColumnDataSource(pd.DataFrame({'hour' : [8]}))
minute = ColumnDataSource(pd.DataFrame({'minute' : [0]}))
ampm = ColumnDataSource(pd.DataFrame({'ampm' : [0]}))
output = ColumnDataSource(pd.DataFrame({'order' : [], 'total_time' : [], 'chance' : [], 'gen' : []}))
timeseries = ColumnDataSource(pd.DataFrame({'order' : [], 'chance' : [], 'gen' : []}))
data_dict = {'x': [],'y': [], 'color': []}
source_table_hist = ColumnDataSource(data=data_dict)

palette = ['#084594', '#2171b5', '#4292c6', '#6baed6', '#9ecae1', '#c6dbef', '#deebf7', '#f7fbff']

#graph base
p = figure(
    toolbar_location="above",
    # tools=TOOLS,
    width=700,
    height=700,
    name = 'base',
    tools = ['tap, wheel_zoom, reset, pan']
    # tooltips=TOOLTIPS
    # x_range=(-74.5, -73.5),
    # y_range=(40, 41)
           )

#map of NYC
p.multi_line('xs',
             'ys',
             source=street_source,
             color='gray',
             line_width=.5,
             alpha = .7,
             name="map"
             )

p.title.text = "Route Optimizer"
p.title.text_font_size = "25px"
p.xaxis.axis_label = "Longitude"
p.yaxis.axis_label = "Latitude"

#points on map
p.circle_cross(source = source,
               x ='x',
               y ='y',
               size=10,
               # color="#990F02",
               fill_alpha=0.2,
               line_width=2,
               name = 'pts'
               )

p.add_tools(HoverTool(names=['map'],
                      show_arrow=False,
                      line_policy='next',
                      tooltips=[("street:", "@full_stree")]
                      )
            )

p.add_tools(HoverTool(names=['pts'],
                      show_arrow=False,
                      line_policy='next',
                      tooltips=[("lon:", "@x"),
                                ("lat:", "@y")]
                      )
            )

#histogram
h = figure(x_range=data_dict['x'],
           height = 300,
           width=700,
           tools="hover",
           tooltips="@x: @y",
           title="Combination Counts",
           toolbar_location="above",)

h.vbar(x ='x',
       top ='y',
       width = .7,
       color='color',
       source=source_table_hist)

h.xaxis.major_label_orientation = 1 #math.pi/2
h.xaxis.axis_label = "Order"
h.yaxis.axis_label = "Count"

#time series
l = figure(title="Fitness",
           y_axis_type="linear",
           tools="hover",
           tooltips="@name",
           plot_height = 300,
           width=700,
           toolbar_location="above",)

l.xaxis.axis_label = 'Generation'
l.yaxis.axis_label = 'Fitness'

#add a dot where the click happened
def callback(event):
    Coords=(event.x, event.y)
    coordList.append(Coords)
    source.data = pd.DataFrame(dict(x=[i[0] for i in coordList], y=[i[1] for i in coordList]))

def solve():
    print('start')

    #prepare inputs
    start_date = pd.DataFrame(date.data)['date'][0]#.to_pydatetime()
    print(start_date)
    start_hour = int(pd.DataFrame(hour.data)['hour'][0]) + int(pd.DataFrame(ampm.data)['ampm'][0])
    print(start_hour)
    start_minute = int(pd.DataFrame(minute.data)['minute'][0])
    print(start_minute)
    start_date = start_date + timedelta(hours=start_hour) + timedelta(minutes=start_minute)
    init_pop = pd.DataFrame(initpop.data)['init_pop'][0]
    num_gens = pd.DataFrame(numgens.data)['num_gens'][0]
    points_df = pd.DataFrame(coordList)
    points_df.columns = ['latitude', 'longitude']
    start_loc = pd.DataFrame(points_df.loc[0]).transpose()
    visit_points = points_df.loc[1:].reset_index()[['latitude', 'longitude']]

    #running the optimization function
    hold = af.get_all(start_loc,
                      visit_points,
                      start_date,
                      init_pop,
                      num_gens)

    hold['chance'] = round(hold['chance'], 3)

    #source data frame
    combos = hold.iloc[0:, :len(hold.columns) - 4]
    a = combos.columns
    hold['order'] = '0->' + combos[a].apply(lambda row: '->'.join((row.values+1).astype(str)), axis=1)

    # table data updates
    table_data = hold.groupby(['order', 'total_time', 'gen']).sum().reset_index()
    table_data = table_data.sort_values(['gen', 'chance'], ascending=[False, False])
    output.data = table_data[['order', 'total_time', 'chance', 'gen']]

    plot_order = af.condense(hold.tail(init_pop)).sort_values('total_time').iloc[0, 0:len(hold.columns) - 5]
    plot_dat = visit_points.reindex(plot_order)
    fullplotdat = pd.DataFrame(start_loc.append(plot_dat)).reset_index()
    line_source.data = fullplotdat
    p.line(x = 'latitude',
           y = 'longitude',
           line_width = 2,
           color = '#6baed6',
           name = 'line',
           source = line_source)

    #histogram data update
    hist_data = hold.groupby('order').count().reset_index()
    color_hold = []
    colors = cycle(palette)
    for i, color in zip(range(len(hist_data)), colors):
        color_hold.append(color)
    groups = list(hist_data['order'])
    count = list(hist_data['gen'])
    data_dict = {'x': groups, 'y': count, 'color': color_hold}
    h.x_range.factors = data_dict['x']  # update existing range (good)
    source_table_hist.data = data_dict

    #line graph / time series update
    line_data = hold.groupby(['order', 'gen']).sum().reset_index()[['order', 'gen', 'chance']]
    line_data = line_data.groupby('order').apply(lambda x: [list(x['chance']), list(x['gen'])]).apply(pd.Series).reset_index()
    line_data.columns = ['order', 'chance', 'gen']
    line_data['color'] = color_hold
    timeseries.data = line_data
    l.multi_line(xs ='gen',
                 ys ='chance',
                 # legend = 'order',
                 line_width=4,
                 line_alpha=0.6,
                 hover_line_alpha=1.0,
                 color = 'color',
                 source = timeseries)
    l.legend.location = 'top_left'
    l.add_tools(HoverTool(show_arrow=False, line_policy='next', tooltips=[
        ('order:','@order')
    ]))
    print('finished')


def update_popsize(attr, old, new):
    initpop.data = pd.DataFrame({'init_pop' : [new]})

def update_numgen(attr, old, new):
    numgens.data = pd.DataFrame({'num_gens' : [new]})

def update_date(attr, old, new):
    date.data = pd.DataFrame({'date': [new]})

def update_hour(attr, old, new):
    hour.data = pd.DataFrame({'hour': [int(new)]})

def update_minute(attr, old, new):
    minute.data = pd.DataFrame({'minute': [int(new)]})

def update_ampm(attr, old, new):
    if new == 'PM':
        ampm.data = pd.DataFrame({'ampm': [12]})
    else :
        ampm.data = pd.DataFrame({'ampm': [0]})

def clear():
    global coordList
    source.data = {k: [] for k in source.data}
    coordList = []
    line_source.data = {k: [] for k in line_source.data}

#data table
columns = [
        TableColumn(field='x', title='longitude'),
        TableColumn(field='y', title='latitude')
    ]
data_table = DataTable(source=source,
                       columns=columns,
                       width=700,
                       height=150)

columns2 = [
        TableColumn(field='order', title='order'),
        TableColumn(field='total_time', title='total time'),
        TableColumn(field='chance', title='chance'),
        TableColumn(field='gen', title='gen')
    ]

data_table_2 = DataTable(source=output,
                         columns=columns2,
                         width=700,
                         height=280)

#double click on map
p.on_event(DoubleTap, callback)

#optimizer button
button = Button(label="Optimize",
                button_type="primary",
                width = 590
                )
button.on_click(solve)

#reset button
reset = Button(label="Reset",
               button_type="default",
               width = 100
               )
reset.on_click(clear)

#dropdown choices
select_hour = Select(title="Hour:",
                     value="8",
                     options=["1", "2", "3", "4", "5", "6",
                                                   "7", "8", "9", "10", "11", "12"],
                     width = 100)
select_hour.on_change('value', update_hour)

select_minute = Select(title="Minute:",
                       value="00",
                       options=["00", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
                                                        "11", "12", "13", "14", "15", "16", "17", "18", "19", "20",
                                                        "21", "22", "23", "24", "25", "26", "27", "28", "29", "30",
                                                        "31", "32", "33", "34", "35", "36", "37", "38", "39", "40",
                                                        "41", "42", "43", "44", "45", "46", "47", "48", "49", "50",
                                                        "51", "52", "53", "54", "55", "56", "57", "58", "59"],
                       width = 100)
select_minute.on_change('value', update_minute)

select_ampm = Select(title="AM/PM:",
                     value="00",
                     options=["AM", "PM"],
                     width = 75)
select_ampm.on_change('value', update_ampm)

#sliders
population_size_input = Slider(start = 5, end = 100, value=10, step=1, title="Population Size")
population_size_input.on_change('value', update_popsize)

generation_input = Slider(start = 2, end = 100, value=5, step=1, title="Number of Generations")
generation_input.on_change('value', update_numgen)

dt_pckr = DatePicker(title='Start Date',
                     min_date=datetime(1900,1,1),
                     max_date=datetime.today().replace(year = datetime.today().year + 5),
                     width = 400)
dt_pckr.on_change('value', update_date)

table1_title = Div(text="""<b>Inputted Locations</b>""")
table2_title = Div(text="""<b>History</b>""")
table2_title = Div(text="""<b>History</b>""")

layout = Row(Column(p,
                    Row(button, reset),
                    table2_title,
                    data_table_2,
                    ),
             Column(
                    Row(dt_pckr, select_hour, select_minute, select_ampm),
                    population_size_input,
                    generation_input,
                    table1_title,
                    data_table,
                    l,
                    h
                    )
            )

curdoc().add_root(layout)
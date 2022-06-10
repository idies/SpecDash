from dash import dash_table
from dash import html
from dash import dcc
from specdash.config import DASH_TABLE_PAGE_SIZE

def get_dash_table(id_prefix, **extra_params):

    params = {
        #'id':{'type':'dashtable','index':id_prefix},
        'id': id_prefix,
        'filter_action': "native",
        'sort_action': "native",
        'sort_mode': "multi",
        'css':[{"selector": ".column-header--delete svg","rule": 'display: "none"'},
                {"selector": ".column-header--delete::before","rule": 'content: "X"'},
               #{'selector': '.export', 'rule': 'position: absolute;left: 13rem;bottom: -2rem;'}, # moves export button below table
               #{'selector': '.show-hide', 'rule': 'position: absolute;left: 17rem;bottom: -2rem !important;'}, # moves toggel button below table
               {'selector':'.dash-spreadsheet-menu', 'rule':'position: absolute;left: 11rem;bottom: -2rem'}
               #{
               #    "selector": 'td.cell--selected *, td.focused *',
               #    "rule": 'backgroundColor: white !important;'
               #}
              ],
        'style_table': {'overflowX': 'scroll','minWidth': '100%','fontSize': '0.8rem'},
        'style_cell': {'whiteSpace': 'normal','wordWrap': 'break-word','height': 'auto','textAlign':"right", 'borderLeft':"0px", 'borderRight':"0px",'borderTop':"0px", 'borderBottom':"0px"},
        'style_header': {'backgroundColor': 'rgb(250,250,250)','fontWeight': 'bold','fontSize': '0.8rem','borderTop':"1px solid rgb(150,150,150)"},
        'style_filter': {'backgroundColor': 'white','borderBottom':'1px rgb(250,250,250)'},
        'export_format': 'xlsx',
        'export_headers': 'display',
        'tooltip_delay': 0,
        'tooltip_duration': None,
        'page_action': 'native',
        'page_size': DASH_TABLE_PAGE_SIZE,
        'persistence':True,
    }

    for key in extra_params.keys():
        params[key] = extra_params[key]

    table = dash_table.DataTable(**params)

    page_size_input = html.Span(['Page size: ',dcc.Input(id=id_prefix+"_page_size_input",type='number',min=0,step=1,value=DASH_TABLE_PAGE_SIZE, style={'maxWidth':'5rem'})])
    return html.Span(children=[table,page_size_input])

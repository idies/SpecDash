//alert("dedW")
//sessionStorage.clear()

var spectral_lines = null
var sky_lines = null
var artificial_lines = null
var nclick_show_error_button = 0
var do_show_error = false
var do_show_photometry = false
var do_show_barchart = false
var do_show_zdistlog = true
var rounding_value = 7 // for rounding a double precision float to single precision and showing it on the UI.
window.PlotlyConfig = {MathJaxConfig: 'local'}
var max_num_traces = null;

$(document).ready(function(){
    //max_num_traces = Number(document.getElementById("max_num_traces").value);
})

window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {

        build_app_data : function(){
            //max_num_traces = Number(document.getElementById("max_num_traces").value);
            max_num_traces = (arguments.length - 1)/2
            data = arguments[arguments.length-1]  // last element (from state)
            if(data != null && data['trace_store_mapping'] != null && data['zdist_store_mapping'] != null){
                trace_store_mapping = data['trace_store_mapping']
                zdist_store_mapping = data['zdist_store_mapping']
                for(trace_name in data['trace_store_mapping']){
                    i = data['trace_store_mapping'][trace_name]
                    trace = arguments[i]
                    if(trace != null){
                        data['traces'][trace_name] = trace
                    }
                }
                for(zdist_name in data['zdist_store_mapping']){
                    i = data['zdist_store_mapping'][zdist_name]
                    zdist = arguments[i + max_num_traces]
                    if(zdist != null){
                        data['redshift_distributions'][zdist_name] = zdist
                    }
                }
                return data
            }else{
                return window.dash_clientside.no_update
            }
        },


        set_page_size : function(value){
            if(value != null && !isNaN(value)){
                return value
            }else{
                return window.dash_clientside.no_update
            }
        },


        toggle_main_page : function(pathname){
            //alert("toggle_main_page: " + pathname + " "+location.pathname)
            if(pathname.endsWith("/docs")){//last check is for jupyterlab  || pathname.startsWith("/proxy/")
                return [{'display': 'none'},{'display': 'block'}]
            }else{
                return [{'display': 'block'},{'display': 'none'}]
            }
        },

        //toggle_loading_modal : function(n1, n2, data, is_open){
        toggle_loading_modal : function(){
            n1 = arguments[0]
            n2 = arguments[1]
            data = arguments[2]
            is_open = arguments[3]
            task_name = dash_clientside.callback_context.triggered.map(t => t['prop_id'])[0]
            if(task_name == "open-loadingmodal-button.n_clicks" || task_name == "close-loadingmodal-button.n_clicks"){
                return !is_open
            }
            return false
        },

        toggle_traces_modal : function(n1, n2, n3, is_open){
            task_name = dash_clientside.callback_context.triggered.map(t => t['prop_id'])[0]
            if(task_name == "open-list-traces-button.n_clicks" || task_name == "close-tracesmodal-button.n_clicks" || task_name == 'save-trace-changes-button.nclicks'){
                return !is_open
            }
            return false
        },

        toggle_info_modal : function(n1, modified_timestamp, data, is_open, header_children, body_children){
            task_name = dash_clientside.callback_context.triggered.map(t => t['prop_id'])[0]
            if(task_name == "close-loadingmodal-button.n_clicks"){
                return [false, "", ""]
            }else if(task_name == "info-message.data" || task_name =="info-message.modified_timestamp"){
                if(data != null && header_children == "" && body_children == ""){
                    header = data["header"]
                    body = data["body"]
                    return [true, header, body]
                }else{
                    return [false, "", ""]
                }
            }else{
                return [false, "", ""]
            }
        },

        set_dropdown_options: function(modified_timestamp, data) {
            options = []
            if(data != null){
                trace_names = Object.keys(data.traces)
                for(i=0; i<trace_names.length; i++){
                    trace_name = trace_names[i]
                    if(data.traces[trace_name].is_visible){
                        options.push({label: trace_name, value: trace_name})
                    }
                }
            }
            return options
        },

        set_regions_dropdown_options: function(data){
            options = []
            if(data != null){
                for(trace_name in data.traces){
                    //if(data.traces[trace_name].spectrum_type == "FIT"){
                    if(data.traces[trace_name].is_visible == true){
                        options.push({label: trace_name, value: trace_name})
                    }
                }
            }
            return options
        },

        set_redshift_dropdown_options: function(modified_timestamp, data) {
            options = []
            if(data != null){
                for(trace_name in data.traces){
                    redshift_array = data.traces[trace_name].redshift
                    if(redshift_array != null){
                        for(i = 0; i < redshift_array.length; i++){
                            redshift = (Number(redshift_array[i])).toFixed(rounding_value)
                            text = "z"+String(i+1)+" = "+redshift + "  " + trace_name
                            options.push({label: text, value: redshift})
                        }

                    }
                }
            }
            return options
        },

        set_lines_redshift : function(redshift_slider_value,redshift_input_value,redshift_dropdown_values ){

            triggered = dash_clientside.callback_context.triggered.map(t => t['prop_id']);
            if(triggered == "redshift-slider.value"){
                z = parseFloat(redshift_slider_value)
                return [window.dash_clientside.no_update, z, []]
            }else if(triggered == "redshift_input.value"){
                z = parseFloat(redshift_input_value)
                return [z, window.dash_clientside.no_update, []]
            }else if (triggered == 'redshift-dropdown.value'){ // dropdown option
                if(redshift_dropdown_values != null){
                    if(typeof redshift_dropdown_values == "string"){
                        z = parseFloat(redshift_dropdown_values)
                    }else{
                        if(redshift_dropdown_values.length > 0){
                            z = parseFloat(redshift_dropdown_values[0])
                        }else{
                            z = window.dash_clientside.no_update
                        }
                    }
                    return [z, z, window.dash_clientside.no_update]
                }else{
                    return [window.dash_clientside.no_update, window.dash_clientside.no_update, window.dash_clientside.no_update]
                }
            }else{
                return [window.dash_clientside.no_update, window.dash_clientside.no_update, window.dash_clientside.no_update]
            }
        },


        set_trace_dropdown_values : function(select_all_traces_button_clicks, data, current_values) {

            triggered = dash_clientside.callback_context.triggered.map(t => t['prop_id']);

            if(triggered=="select_all_traces_button.n_clicks"){
                values = []
                if(data != null){
                    trace_names = Object.keys(data.traces)
                    // check number of traces that should be visible:
                    visible_trace_names = []
                    for(trace_name in data['traces']){
                        if(data['traces'][trace_name].is_visible == true){
                            visible_trace_names.push(trace_name)
                        }
                    }
                    if(current_values.length < visible_trace_names.length){
                        // add all visible traces that were not previously selected
                        for(i=0; i<trace_names.length; i++){
                            trace_name = trace_names[i]
                            values.push(trace_name)
                        }
                    }

                    /*
                    if(current_values.length != trace_names.length){
                        for(i=0; i<trace_names.length; i++){
                            trace_name = trace_names[i]
                            values.push(trace_name)
                        }
                    }
                    */
                }
                return values

            }else if(triggered == "store.data"){
                values = []
                if(data != null){
                    // add all current values that are inside data:
                    for(trace_name in data['traces']){
                        for(current_value in current_values){
                            if(current_value == data['traces'][trace_name] && data['traces'][trace_name].is_visible == true){
                                values.push(current_value)
                            }
                        }
                        // add only those with no ancestors, i.e., are object spectra and not sky, model, etc
                        trace = data['traces'][trace_name]
                        //if(trace.spectrum_type == "OBJECT" && trace.is_visible == true  && !(trace_name in values)){
                        if(trace.ancestors.length == 0 && trace.is_visible == true  && !(trace_name in values)){
                            values.push(trace_name)
                        }
                    }

                    values = Array.from(new Set(values));
                }
                return values
            }else{
                return window.dash_clientside.no_update
            }

        },

        set_current_data_selection_table: function(selected_data, data, wavelength_unit, flux_unit){
            table_rows = []
            column_names = []
            column_names.push({id:'trace',name:'trace', hideable: true})
            column_names.push({id:'wavelength',name:'wavelength', hideable: true})
            column_names.push({id:'flux',name:'flux', hideable: true})
            column_names.push({id:'index',name:'index', hideable: true})
            column_names.push({id:'units',name:'units', hideable: true})
            //column_names.push({id:'flux unit',name:'flux unit', hideable: true})


            if(data != null && selected_data != null){
                trace_names = Object.keys(data['traces'])
                curve_mapping = get_curve_index_mapping(data)

                for(i=0;i<selected_data["points"].length;i++){
                    point = selected_data["points"][i]
                    row = {'trace':curve_mapping[point['curveNumber']],
                            'wavelength':String(point['x']),'flux':String(point['y']),'index':String(point['pointIndex']),
                            'units': wavelength_unit + ", " + flux_unit}
                    table_rows.push(row)
                }
            }
            return [table_rows,column_names,0,[]]
        },

        set_fitted_models_table: function(modified_timestamp, data) {

            let column_names = [{id:'no data','name':'no data'}]
            let table_rows = []
            allowed_cols = ['trace_name','original_trace','model','wavelength_unit','flux_unit']
            if(data != null){
                for(fitted_model_name in data['fitted_models']){
                    fitted_model = data['fitted_models'][fitted_model_name]
                    for(i=0;i<fitted_model['parameter_names'].length;i++){
                        row = {}
                        for(j=0;j<allowed_cols.length;j++){
                            row[allowed_cols[j]] = fitted_model[allowed_cols[j]]
                        }
                        param_name = fitted_model['parameter_names'][i]
                        row['parameter_name'] = param_name
                        row['parameter_value'] = String(fitted_model['parameter_values'][param_name])
                        row['parameter_error'] = String(fitted_model['parameter_errors'][param_name])
                        table_rows.push(row)
                    }
                }
                if(table_rows.length > 0){
                    column_names = []
                    for(col in table_rows[0]){
                        column_names.push({id:col,name:col, hideable: true})
                    }
                }
                return [table_rows,column_names]
            }else{
                return [table_rows,column_names]
            }
        },

        set_traces_table: function(data, color_picker_value, active_cell_value, table_data_rows) {
            let col_name = 'color'
            let table_rows = []
            let tooltip_rows = []
            let column_names = []
            let style_data_conditional = []
            triggered = dash_clientside.callback_context.triggered.map(t => t['prop_id']);

            if(data != null){
                if(triggered =="store.data"){
                    table = build_traces_table(data)
                    return [table.table_rows,table.column_names,table.style_data_conditional,window.dash_clientside.no_update]

                }else if(triggered =="traces_table.active_cell"){
                    if(active_cell_value['column_id'] == col_name){
                        rgb_string = table_data_rows[active_cell_value['row']][col_name]
                        rgb_array = parse_color(rgb_string)
                        rgb = {'rgb':{'r':rgb_array[0], 'g':rgb_array[1], 'b':rgb_array[2], 'a':1}}
                        return [window.dash_clientside.no_update, window.dash_clientside.no_update, window.dash_clientside.no_update, rgb]
                    }else{
                        return [table_data_rows, window.dash_clientside.no_update, window.dash_clientside.no_update, window.dash_clientside.no_update]
                    }
                }else if(triggered =="color_picker.value"){
                    cell_value = 'rgb('+String(color_picker_value['rgb']['r']) + "," + String(color_picker_value['rgb']['g']) + "," + String(color_picker_value['rgb']['b']) + ")"
                    index = active_cell_value['row']
                    trace_name = Object.keys(data['traces'])[index]
                    data['traces'][trace_name].color = cell_value
                    table = build_traces_table(data)
                    table_data_rows[index].color = cell_value
                    return [table_data_rows, window.dash_clientside.no_update, table.style_data_conditional, window.dash_clientside.no_update]
                }

            }
            return [window.dash_clientside.no_update,window.dash_clientside.no_update,window.dash_clientside.no_update,window.dash_clientside.no_update]
        },

        set_measured_lines_table: function(modified_timestamp, data) {

            let column_names = []
            let table_rows = []

            if(data != null){
                if(data['traces'] != {}){
                    let first_column_name = "object"
                    for(trace_name in data['traces']){
                        speclines = data['traces'][trace_name]['spectral_lines']
                        first_column = {object:trace_name}
                        if(speclines != null && speclines.length > 0){
                            if(column_names.length == 0){
                                column_names.push({id:'object',name:'object'})
                                col_names = Object.keys(speclines[0])
                                for(i=0;i<col_names.length;i++){
                                    column_names.push({id:col_names[i],name:col_names[i], hideable: true})
                                }
                            }
                            for(i=0;i<speclines.length;i++){
                                //concatenating objects and adding to data array:
                                specline = speclines[i]
                                for(info in specline){
                                    specline[info] = String(specline[info]) // this makes the column sortable
                                }
                                row = { ...first_column, ...specline }
                                table_rows.push(row)
                            }
                        }
                    }

                }
            }
            if(column_names.length == 0){
                column_names = [{id:'no data','name':'no data'}]
            }
            return [table_rows,column_names]
        },

        set_line_analysis_table: function(modified_timestamp, data) {

            let column_names = []
            let table_rows = []

            if(data != null){
                if(data['traces'] != {}){
                    let first_column_name = "object"
                    for(trace_name in data['traces']){
                        speclines = data['traces'][trace_name]['spectral_lines']
                        spectrum_type = data['traces'][trace_name]['spectrum_type']
                        first_column = {object:trace_name}
                        if(speclines != null && speclines.length > 0 && spectrum_type == "LINE"){
                            if(column_names.length == 0){
                                column_names.push({id:'object',name:'object'})
                                col_names = Object.keys(speclines[0])
                                for(i=0;i<col_names.length;i++){
                                    column_names.push({id:col_names[i],name:col_names[i], hideable: true})
                                }
                            }
                            for(i=0;i<speclines.length;i++){
                                //concatenating objects and adding to data array:
                                specline = speclines[i]
                                for(info in specline){
                                    specline[info] = String(specline[info]) // this makes the column sortable
                                }
                                row = { ...first_column, ...specline }
                                table_rows.push(row)
                            }
                        }
                    }

                }
            }
            if(column_names.length == 0){
                column_names = [{id:'no data','name':'no data'}]
            }
            return [table_rows,column_names]
        },

        set_info_content: function(modified_timestamp, data) {
            if(data != null){
                var tab = ""
                tab += "<div class='container-fluid'>"
                tab += "<div class='row'>"

                for(trace_name in data['traces']){
                    metadata = data['traces'][trace_name]['metadata']
                    is_visible = data['traces'][trace_name]['is_visible']
                    // create header:
                    if(metadata != null && Object.keys(metadata).length > 0 && is_visible){
                        tab += "<div class='col-sm-auto'>"
                        //tab += "<div class='container meta' style=''>"
                        tab += "<span><u><strong>"+trace_name+"</strong></u></span>"
                        tab += "<table>"
                        tab += "<tbody>"
                        //tab += "<caption><u>" + trace_name + "</u></caption>"
                        //add properties:
                        for(parameter_name in metadata){
                            parameter_value = (metadata[parameter_name])
                            //round the float values:
                            if(Number(parameter_value) === parameter_value && parameter_value % 1 !== 0){
                                parameter_value = String(parameter_value.toFixed(rounding_value))
                            }
                            tab += "<tr><td>" +  parameter_name + ":</td><td>" + parameter_value + "</td></tr>"
                        }
                        //tab += "<tr><td>   </td><td>  </td></tr>"
                        tab += "</tbody>"
                        tab += "</table>"
                        tab += "<br></br>"
                        //tab += "</div>" // closing container div
                        tab += "</div>" // closing column
                    }
                }
                tab += "</div>"
                tab += "</div>"
                return tab
            }else{
                return ""
            }
        },

        set_masks_dropdown: function(modified_timestamp, data){

            mask_dropdown_options = []

            catalogs_list = []
            options_ids = {}
            if(data != null && data['traces'] != null){

                for( trace_name in data['traces']){
                    //adding "all" entry:
                    catalog = data['traces'][trace_name].catalog
                    label_all = trace_name + " ALL MASKS"
                    options_for_all_entry = []
                    options_ids = {} // stores the IDs of all masks already added to the mask_dropdown_options, so that there are no duplicates
                    if( data['traces'][trace_name]['masks'] != null && data['traces'][trace_name]['masks']['mask_values'] != null){
                        for(mask_id in data['traces'][trace_name]['masks']['mask_values']){
                            bit = data['traces'][trace_name]['masks']['mask_values'][mask_id].bit
                            catalog = data['traces'][trace_name]['masks']['mask_values'][mask_id].catalog
                            name = data['traces'][trace_name]['masks']['mask_values'][mask_id].name
                            label_value = trace_name + " " + name + " " + bit
                            options_for_all_entry.push({label:label_value, value:{id:label_value, trace:trace_name, bit:bit, catalog:catalog, name:name, is_all:false}})
                        }
                        if(options_ids[label_all] == null){
                            val = JSON.stringify({id:label_all, trace:trace_name, bit:null, catalog:catalog, is_all:true, options_for_all_entry:options_for_all_entry})
                            mask_option = {label:label_all, value:val}
                            mask_dropdown_options.push(mask_option)
                            options_ids[label_all] = mask_option
                        }

                        //adding single mask entries
                        for(mask_id in data['traces'][trace_name]['masks']['mask_values']){
                            bit = data['traces'][trace_name]['masks']['mask_values'][mask_id].bit
                            catalog = data['traces'][trace_name]['masks']['mask_values'][mask_id].catalog
                            name = data['traces'][trace_name]['masks']['mask_values'][mask_id].name
                            label_value = trace_name + " " + name + " " + bit

                            if(options_ids[label_value] == null){
                                mask_option = {label:label_value, value:JSON.stringify({id:mask_id, trace:trace_name, bit:bit, catalog:catalog, name:name, is_all:false})}
                                mask_dropdown_options.push(mask_option)
                                options_ids[label_value] = mask_option
                            }
                        }
                    }

                }
            }
            return mask_dropdown_options
        },

        set_figure: function(modified_timestamp, spectral_lines_switch, sky_lines_switch, artificial_lines_switch, redshift, spectral_lines_dropdown,
                            sky_lines_dropdown, artificial_lines_dropdown, mask_switch, mask_dropdown, show_error_button_nclicks, data, specmodels_dropdown,
                            show_photometry_button_nclicks, show_barchart_button_nclicks, spectral_lines_dict, sky_lines_dict, artificial_lines_dict, trace_dropdown, graph_settings){

            triggered = dash_clientside.callback_context.triggered.map(t => t['prop_id']);
            if(triggered == "show_photometry_button.n_clicks"){
                do_show_photometry = !do_show_photometry
            }
            if(triggered == "show_barchart_button.n_clicks"){
                do_show_barchart = !do_show_barchart
            }

            if(show_error_button_nclicks > nclick_show_error_button){
                nclick_show_error_button = show_error_button_nclicks
                if(do_show_error == true)
                    do_show_error=false
                else
                    do_show_error=true
            }

            res = build_figure_data(data, spectral_lines_switch, redshift, spectral_lines_dropdown, spectral_lines_dict, trace_dropdown, specmodels_dropdown, do_show_error, do_show_barchart)
            figure_data = res[0]
            graph_trace_info = res[1]
            //x_range = get_x_range(data)
            figure_layout = build_figure_layout(data, spectral_lines_switch=spectral_lines_switch, sky_lines_switch, artificial_lines_switch, redshift,
                                                spectral_lines_dropdown, sky_lines_dropdown, artificial_lines_dropdown, spectral_lines_dict, sky_lines_dict, artificial_lines_dict, mask_switch, mask_dropdown, trace_dropdown, do_show_photometry, graph_settings)
            //console.log(JSON.stringify(figure_layout.xaxis))
            return [{data:figure_data, layout:figure_layout},graph_trace_info]
        },

        set_zdist_figure: function(modified_timestamp, data, show_zdistlog_button_nclicks, trace_dropdown) {

            triggered = dash_clientside.callback_context.triggered.map(t => t['prop_id']);
            if(triggered == "show_zdistlog_button.n_clicks"){
                do_show_zdistlog = !do_show_zdistlog
            }
            figure_data = build_zdist_figure_data(data, trace_dropdown)
            figure_layout = build_zdist_figure_layout(data, trace_dropdown, do_show_zdistlog)
            //console.log(JSON.stringify(figure_layout.xaxis))
            return {data:figure_data, layout:figure_layout}
        },

        set_dropdown_options_for_specmodels: function(modified_timestamp, data) {
            options = []
            if(data != null){
                zdist_names = Object.keys(data.redshift_distributions)
                for(i=0; i<zdist_names.length; i++){
                    trace_name = zdist_names[i]
                    for(j=0;j<data.redshift_distributions[trace_name].model_names.length;j++){
                        z = data.redshift_distributions[trace_name].redshift_solutions[j]
                        model_name = data.redshift_distributions[trace_name].model_names[j]
                        short_model_name = data.redshift_distributions[trace_name].ancestors[0]
                        short_model_name = get_short_name(short_model_name, max_name_length=20, halfname_length=10)
                        z_index = j+1
                        display_name = "z"+z_index+"="+ z + " model"+z_index + " " + short_model_name,
                        options.push({label: display_name, value: model_name})
                    }
                }
            }
            return options
        },
    }
});

function get_short_name(name, max_name_length=10, halfname_length=5){
    short_name = name
    if(short_name.length > max_name_length){
        short_name = short_name.substring(0,halfname_length) + "..." + short_name.substring(short_name.length-halfname_length,short_name.length)
    }
    return short_name
}


function get_data_ranges(data){
    var x_min=0.0
    var x_max=1.0
    var y_min=0.0
    var y_max=1.0
    if(data == null || data.traces == null){
        return {x_range:[x_min,x_max], y_range:[y_min,y_max]}
    }
    trace_names = Object.keys(data.traces)
    if(trace_names.length == 0){
        return {x_range:[x_min,x_max], y_range:[y_min,y_max]}
    }else{
        x_min = Number.MAX_VALUE
        x_max = -Number.MAX_VALUE
        y_min = Number.MAX_VALUE
        y_max = -Number.MAX_VALUE
        for(i=0; i<trace_names.length; i++){
            trace_name = trace_names[i]
            if(data.traces[trace_name].is_visible == true ){
                x_min = Math.min(x_min, Math.min.apply(Math, data.traces[trace_name].wavelength))
                x_max = Math.max(x_max, Math.max.apply(Math, data.traces[trace_name].wavelength))
                y_min = Math.min(y_min, Math.min.apply(Math, data.traces[trace_name].flux))
                y_max = Math.max(y_max, Math.max.apply(Math, data.traces[trace_name].flux))
            }
        }
        return {x_range:[x_min,x_max], y_range:[y_min,y_max]}
    }
}

function get_flux_unit(data){
    return "Flux"
}

function get_x_axis_label(data){
    label = "\\text{Wavelength}"
    unit = get_wavelength_unit(data)
    if(unit != ""){
        label = label + "\\quad [ \\text{" + unit + "} ]"
    }
    return "$" + label + "$"
}

function get_y_axis_label(data){
    unit = get_flux_unit(data)
    if(unit != ""){
        if(unit == "F_lambda"){
            label = "$\\text{F}_{\\lambda} \\quad [\\text{erg/s/cm}^2/\\text{A}]$"
        }else if(unit == "F_nu"){
            label = "$\\text{F}_{\\nu} \\quad [\\text{erg/s/cm}^2/\\text{Hz}]$"
        }else if(unit == "AB_magnitude"){
            label = "$\\text{F}_{\\text{AB}} \\quad [\\text{magnitude}]$"
        }else if(unit == "Jansky"){
            label = "$\\text{Jansky}$"
        }else{
            label = "Flux"
        }
    }else{
        label = "Flux"
    }
    return label
}



function get_wavelength_unit(data){

    if(data == null){
        return ""
    }
    trace_names = Object.keys(data.traces)
    if(trace_names.length == 0){
        return ""
    }else{
        // getting unit from first trace, assumes all traces have same units
        trace_name = trace_names[0]
        if(data.traces[trace_name].wavelength_unit == null){
            return ""
        }else{
            unit = data.traces[trace_name].wavelength_unit
            return unit
        }
    }
}

function get_flux_unit(data){

    if(data == null){
        return ""
    }
    trace_names = Object.keys(data.traces)
    if(trace_names.length == 0){
        return ""
    }else{
        // getting unit from first trace, assumes all traces have same units
        trace_name = trace_names[0]
        if(data.traces[trace_name].flux_unit == null){
            return ""
        }else{
            unit = data.traces[trace_name].flux_unit
            return unit
        }
    }
}


function get_plot_type(do_show_barchart, trace_name, trace_dropdown_names){
    if(do_show_barchart && trace_dropdown_names.includes(trace_name)){
        return 'bar'
    }else{
        return 'scattergl'
    }
}


function build_figure_data(data, spectral_lines_switch, redshift, spectral_lines_dropdown, spectral_lines_dict, trace_dropdown_names, specmodels_dropdown, do_show_error, do_show_barchart){

    traces = []
    graph_trace_info = {curve_mapping:{}, curve_mapping_rev:{}}

    var plottype = "scattergl"
    if(do_show_barchart){
        plottype = "bar"
    }

    if(do_show_barchart)
    wavelength_unit = get_wavelength_unit(data)
    //ranges = get_data_ranges(data)

    if(data != null){
        trace_names = Object.keys(data.traces)
        curve_index = 0
        for(i=0; i<trace_names.length; i++){
            trace_name = trace_names[i]

            var add_error_bounds = do_show_error && trace_dropdown_names.includes(trace_name) && data.traces[trace_name].flux_error != null && data.traces[trace_name].flux_error.length>0
            //var fill_color = add_alpha_to_rgb(data.traces[trace_name].color,0.2)
            if(data.traces[trace_name].is_visible==true || (specmodels_dropdown != null && specmodels_dropdown.includes(trace_name)) ){

                if(add_error_bounds){
                    var flux_lower_bound = []
                    var wavelength_lower_bound = []
                    for(j=0;j<data.traces[trace_name].flux.length;j++){
                        if(data.traces[trace_name].flux_unit == "AB_magnitude"){
                            if(data.traces[trace_name].flambda_error[j] != null){
                                f = data.traces[trace_name].flambda[j] + data.traces[trace_name].flambda_error[j]
                                w = data.traces[trace_name].wavelength[j]
                                w_u = data.traces[trace_name].wavelength_unit
                                //ab = data.traces[trace_name].flux[j]
                                ab_bound = flambda_to_abmag(f,w,w_u)
                                flux_lower_bound.push(ab_bound)
                                wavelength_lower_bound.push(w)
                            }
                        }else{
                            if(data.traces[trace_name].flux_error[j] != null){
                                flux_lower_bound.push(data.traces[trace_name].flux[j] - data.traces[trace_name].flux_error[j])
                                wavelength_lower_bound.push(data.traces[trace_name].wavelength[j])
                            }
                        }
                    }

                    lower_error_trace = {   name:trace_name + "_lower_error_bound",
                                            x: wavelength_lower_bound,
                                            y: flux_lower_bound,
                                            mode: "lines",
                                            type: get_plot_type(do_show_barchart, trace_name, trace_dropdown_names),
                                            xaxis: "x",
                                            yaxis: "y",
                                            line:{color:data.traces[trace_name].color, width:1.0*data.traces[trace_name].linewidth},
                                            showlegend : false,
                                            hoverinfo:"x+y",
                                            opacity:0.3,
                                            //fill: "tonexty", fillcolor: fill_color,
                                        }
                }

                trace = {   name:trace_name,
                            x: data.traces[trace_name].wavelength,
                            y: data.traces[trace_name].flux,
                            mode: "markers+lines",
                            //type: 'scatter',
                            type: get_plot_type(do_show_barchart, trace_name, trace_dropdown_names),
                            //visible: data.traces[trace_name].is_visible,
                            color: data.traces[trace_name].color,
                            xaxis: "x",
                            yaxis: "y",
                            marker:{size: 1.0*data.traces[trace_name].linewidth, color:data.traces[trace_name].color },
                            line:{ color:data.traces[trace_name].color, width:1.0*data.traces[trace_name].linewidth }
                }
                if(add_error_bounds){
                    trace.error_y = {type:'data',visible:true, array:data.traces[trace_name].flux_error,thickness:0.5, width:0.5}
                }



                if(add_error_bounds){
                    var flux_upper_bound = []
                    var wavelength_upper_bound = []
                    for(j=0;j<data.traces[trace_name].flux.length;j++){
                        if(data.traces[trace_name].flux_unit == "AB_magnitude"){
                            if(data.traces[trace_name].flambda_error[j] != null){
                                f = data.traces[trace_name].flambda[j] - data.traces[trace_name].flambda_error[j]
                                w = data.traces[trace_name].wavelength[j]
                                w_u = data.traces[trace_name].wavelength_unit
                                //ab = data.traces[trace_name].flux[j]
                                ab_bound = flambda_to_abmag(f,w,w_u)
                                flux_upper_bound.push(ab_bound)
                                wavelength_upper_bound.push(w)
                            }
                        }else{
                            if(data.traces[trace_name].flux_error[j] != null){
                                flux_upper_bound.push(data.traces[trace_name].flux[j] + data.traces[trace_name].flux_error[j])
                                wavelength_upper_bound.push(data.traces[trace_name].wavelength[j])
                            }
                        }

                    }

                    upper_error_trace = {   name:trace_name + "_upper_error_bound",
                                            x: wavelength_upper_bound,
                                            y: flux_upper_bound,
                                            mode: "lines",
                                            type: get_plot_type(do_show_barchart, trace_name, trace_dropdown_names),
                                            xaxis: "x",
                                            yaxis: "y",
                                            line:{color:data.traces[trace_name].color, width:1.0*data.traces[trace_name].linewidth},
                                            showlegend : false,
                                            hoverinfo:"x+y",
                                            //fill: "tonexty", fillcolor: fill_color,
                                            opacity:0.3
                    }

                }
                traces.push(trace)
                graph_trace_info.curve_mapping[trace.name] = curve_index
                graph_trace_info.curve_mapping_rev[curve_index] = trace.name
                curve_index++
            }

        }
    }
    return [traces,graph_trace_info]
}

function build_zdist_figure_data(data, trace_dropdown){

    traces = []

    if(data != null){
        zdist_names = Object.keys(data.redshift_distributions)
        for(i=0; i<zdist_names.length; i++){
            trace_name = zdist_names[i]
            trace = {   name:trace_name,
                        x: data.redshift_distributions[trace_name].redshift_array,
                        y: data.redshift_distributions[trace_name].probability_array,
                        mode: "lines",
                        //type: 'scatter',
                        type: 'scattergl',
                        visible: data.redshift_distributions[trace_name].is_visible,
                        color: data.redshift_distributions[trace_name].color,
                        xaxis: "x",
                        yaxis: "y",
                        marker:{size: 1.0, color:data.redshift_distributions[trace_name].color },
                        line:{ color:data.redshift_distributions[trace_name].color, width:1.0 },
                        showlegend : false,
            }
            traces.push(trace)
            for(j=0;j<data.redshift_distributions[trace_name].model_names.length;j++){
                z = data.redshift_distributions[trace_name].redshift_solutions[j]
                short_name = data.redshift_distributions[trace_name].ancestors[0]
                short_name = get_short_name(short_name, max_name_length=20, halfname_length=10)
                z_index = j+1
                trace = {   name: "z"+z_index+"="+ z + " model"+ z_index + " " + short_name,
                            x: [data.redshift_distributions[trace_name].solution_coordinates[j][0] ],
                            y: [data.redshift_distributions[trace_name].solution_coordinates[j][1] ],
                            mode: "markers",
                            type: 'scattergl',
                            visible: data.redshift_distributions[trace_name].is_visible,
                            color: data.redshift_distributions[trace_name].color,
                            xaxis: "x",
                            yaxis: "y",
                            marker:{size: 10.0, color:data.redshift_distributions[trace_name].color, line: {color: 'black', width:1}, },
                            showlegend : true,
                }
                traces.push(trace)
            }

        }

    }
    return traces
}

function build_zdist_figure_layout(data, trace_dropdown = []){
    // https://plotly.com/javascript/reference/layout/#layout-legend
    var legend = {
        font: { size:12, color:"black", family:"Courier New, monospace"},
        orientation: 'h',
        y: -0.23,
        xanchor: 'left',
        x: 0.0,
    }
    shapes = []
    annotations = []

    var yscale_type = 'linear'
    if(do_show_zdistlog){
        yscale_type = 'log'
    }


    var viewportheight = window.innerHeight
    var height = 0.3*viewportheight

    var layout = {
        showlegend: true,
        dragmode: "pan",
        hovermode: "x",
        hoverlabel: {bgcolor:"white", bordercolor: "black", align: "left", font:{font_family:"Rockwell", size:20, color:"black"}},
        font: {family: "Courier New, monospace", size: 18, color: "#7f7f7f"},
        xaxis: {anchor: "y", title: {text: "redshift"}, showgrid:false, automargin: true, zeroline: false, showline: false, ticks: 'outside'},
        yaxis: {anchor: "x", title: "PDF", type: yscale_type, showgrid:false, showexponent: 'last', exponentformat: 'power', automargin: true, showline: true, ticks: 'inside', zeroline: true},
        font:{family:"Courier New, monospace", size:12, color:"black"},
        plot_bgcolor:'rgb(255,255,255)',
        margin:{"l": 0, "r": 0, "t": 20, 'b':0},
        clickmode:'event+select',
        height: height,
        shapes: shapes,
        annotations: annotations,
        uirevision: true,
        legend: legend,
    }
    return layout
}


function get_line_definitions(spectral_lines_dropdown, spectral_lines, ranges, wavelength_unit, redshift=0, line_color="grey", line_opacity=0.5, dash){

        annotations = []
        shapes = []
        spec_lines = []
        if(spectral_lines_dropdown.includes('all')){
            for(line in spectral_lines){
                spec_lines.push(spectral_lines[line])
            }
        }else{
            for(i=0;i<spectral_lines_dropdown.length;i++){
                line_name = spectral_lines_dropdown[i]
                if(line_name in spectral_lines){
                    spec_lines.push(spectral_lines[line_name])
                }
            }
        }

        for(i=0; i < spec_lines.length;i++){
            line = spec_lines[i]
            x0 = (1.0+redshift)*line.lambda
            line_label = line.name
            line_label = line.label
            if(line_label.startsWith('$') & line_label.endsWith('$')){
                line_label = line_label.substring(0, line_label.length - 1) + Math.round(line.lambda) + "$"
            }else{
                line_label = line_label + Math.round(line.lambda)
            }

            if(wavelength_unit == "nanometer")
                x0 = x0/10.0
            x1=x0
            // need to include only lines within the range of data since otherwise the plotted area will be too big compared to the spectra.
            if(x0 >= ranges.x_range[0] && x0 <= ranges.x_range[1]){


                if(i % 3 == 0){
                    y_line_annotation = 1.0
                }else if(i % 3 == 1){
                    y_line_annotation = 1.02
                }else{
                    y_line_annotation = 1.04
                }

                y0=0
                y1=1

                line = {type: 'line', name:line_label,  layer:'above', xref:'x', yref: 'paper', y0: y0, y1: y1, x0: x0, x1: x1, line:{ width:0.5, color:line_color}, opacity:line_opacity, dash:dash}
                shapes.push(line)

                annotation = {showarrow: false, text: line_label, align: "center",x: x0, xanchor: "center", y: y_line_annotation, yanchor: "bottom", yref:"paper", font:{size:9, family:"Arial",color:line_color}, opacity:1}
                annotations.push(annotation)
            }
        }
        return [annotations,shapes]
}

function foo(x, ...args) {
  console.log(x, args, ...args, arguments);
}

function build_figure_layout(data, spectral_lines_switch=false, sky_lines_switch=false, artificial_lines_switch=false, redshift=0.0, spectral_lines_dropdown = [], sky_lines_dropdown = [], artificial_lines_dropdown = [], spectral_lines_dict = [], sky_lines_dict = [], artificial_lines_dict = [], mask_switch=false, mask_dropdown = [], trace_dropdown = [], do_show_photometry=false, graph_settings = null){

    if(spectral_lines == null){
        spectral_lines = JSON.parse(spectral_lines_dict)
    }

    if(sky_lines == null){
        sky_lines = JSON.parse(sky_lines_dict)
    }

    if(artificial_lines == null){
        artificial_lines = JSON.parse(artificial_lines_dict)
    }

    x_axis_label = get_x_axis_label(data)
    y_axis_label = get_y_axis_label(data)
    wavelength_unit = get_wavelength_unit(data)
    flux_unit = get_flux_unit(data)
    ranges = get_data_ranges(data)

    var annotations = []
    var shapes = [] // https://plotly.com/python/reference/#layout-shapes

    if(do_show_photometry & data != null){

        x0 = 0.05 // paper normalized coordinates
        delta_x0 = 0.075
        delta_y0 = 0.05
        for(i=0; i< trace_dropdown.length;i++){
            y0 = 0.90 // paper normalized coordinates
            trace_name = trace_dropdown[i]

            if(data['traces'][trace_name] != null){
                photometry_dict = data['traces'][trace_name]['photometry']
                if(photometry_dict != null){
                    color = data['traces'][trace_name]['color']
                    //console.log(photometry_dict)
                    for(band in photometry_dict){
                        //console.log(band)
                        photometry_text = band + " : " + (Number(photometry_dict[band])).toFixed(rounding_value)
                        //console.log(photometry_text)
                        annotation = {showarrow: false, text:photometry_text , align: "left",x: x0, xanchor: "center", y: y0, yanchor: "bottom", xref:"paper", yref:"paper", font:{size:12, family:"Arial",color:color}, opacity:1.0}
                        annotations.push(annotation)
                        y0 = y0 - delta_y0
                    }
                    x0 = x0 + delta_x0
                }
            }
        }
    }


    // adding spectral lines
    if(spectral_lines_switch == true){
        definitions  = get_line_definitions(spectral_lines_dropdown, spectral_lines, ranges, wavelength_unit, redshift=redshift, line_color="grey", line_opacity=0.5, dash="solid")
        annotations = annotations.concat(definitions[0])
        shapes = shapes.concat(definitions[1])
    }

    // adding sky lines
    if(sky_lines_switch == true){
        definitions  = get_line_definitions(sky_lines_dropdown, sky_lines, ranges, wavelength_unit, redshift=0, line_color="#6fa9ff", line_opacity=0.5, dash="dash")
        annotations = annotations.concat(definitions[0])
        shapes = shapes.concat(definitions[1])
    }

    // adding artificial lines
    if(artificial_lines_switch == true){
        definitions  = get_line_definitions(artificial_lines_dropdown, artificial_lines, ranges, wavelength_unit, redshift=0, line_color="#8a5151", line_opacity=0.5, dash="dashdot")
        annotations = annotations.concat(definitions[0])
        shapes = shapes.concat(definitions[1])
    }


    // adding masks

    if(mask_switch == true){
        //var selected_masks = []
        var selected_masks = {}
        for(i=0;i<mask_dropdown.length;i++){
            mask = JSON.parse(mask_dropdown[i])
            //selected_masks.push({'id':mask.id, 'catalog':mask.catalog,'bit':parseInt(mask.bit)})

            if(mask.is_all == true){
                options_for_all_entry = mask.options_for_all_entry
                for(j=0;j<options_for_all_entry.length;j++){
                    option_for_all_entry = options_for_all_entry[j]
                    selected_masks[option_for_all_entry.label] = option_for_all_entry
                }
            }else{
                if(selected_masks[mask.id] == null){
                    selected_masks[mask.id] = {label:mask.id, value:{id:mask.id, trace:mask.trace, name:mask.name, catalog:mask.catalog, bit:parseInt(mask.bit)}}
                }
            }
        }

        // plot masks for each trace:
        if(data != null){

            for(trace_name in data['traces']){

                selected_bit_list = []
                selected_masks_in_trace = []
                for(mask in selected_masks){
                    if(selected_masks[mask].value.trace == trace_name){
                        selected_masks_in_trace.push(selected_masks[mask].value)
                    }
                }

                if(selected_masks_in_trace.length > 0){


                    mask_color = data['traces'][trace_name].color
                    //mask_color = "rgb(211,211,211)"
                    trace_catalog = data['traces'][trace_name]['catalog']
                    mask = data['traces'][trace_name]['masks']['mask']
                    wavelength_array = data['traces'][trace_name]['wavelength']

                    for(mask_bit in mask){
                        mask_bit2 = parseInt(mask_bit)

                        bits_in_this_region = []
                        rect_label = ""
                        for(k=0;k<selected_masks_in_trace.length;k++){
                            selected_bit = parseInt(selected_masks_in_trace[k].bit)
                            if( (mask_bit2 & 2**selected_bit) != 0){
                                bits_in_this_region.push(selected_bit)
                                //rect_label = rect_label + " " + String(selected_masks_in_trace[k].id)
                                short_trace_name = String(selected_masks_in_trace[k].trace)
                                max_name_length = 10
                                halfname_length = 5
                                if(short_trace_name.length > max_name_length){
                                    short_trace_name = short_trace_name.substring(0,halfname_length) + "..." + short_trace_name.substring(short_trace_name.length-halfname_length,short_trace_name.length)
                                }
                                rect_label = rect_label + short_trace_name + "<br>" + String(selected_masks_in_trace[k].name) + "<br>"
                            }
                        }
                        if(bits_in_this_region.length > 0){
                            // add masked region
                            wavelength_indices = mask[mask_bit]
                            for(j=0;j<wavelength_indices.length;j++){
                                indices = wavelength_indices[j]
                                x0 = wavelength_array[indices[0]]
                                x1 = wavelength_array[indices[1]]
                                y0 = 0.0
                                y1 = 1.0
                                if(x0 >= ranges.x_range[0] && x0 <= ranges.x_range[1]){
                                    rectangle =  {type: 'rect', name:rect_label,  layer:'below', xref:'x', yref: 'paper', y0: y0, y1: y1, x0: x0, x1: x1, line:{ width:1.0, color:mask_color, opacity:0.2}, opacity:0.2, fillcolor:mask_color}
                                    shapes.push(rectangle)
                                    annotation = {showarrow: false, text: rect_label, align: "center", x: (x0+x1)/2.0, xref:'x', xanchor: "center", y: y0, yanchor: "bottom", yref:"paper", font:{size:11, family:"Arial",color:"black"}, opacity:0.4}
                                    annotations.push(annotation)
                                }
                            }

                        }
                    }
                }

            }
        } // end if

    }

    // https://plotly.com/javascript/reference/layout/#layout-legend
    var legend = {
        font: { size:9, color:"black", family:"Courier New, monospace"},
        orientation: 'h',
        y: -0.15,
        xanchor: 'left',
        x: 0.0,
        //title: {text:"legend title", side:'top'},
        //x:0.90,
        //y:1.2,
    }

    x_axis = {anchor: "y",  title: {text: x_axis_label}, showgrid:false, automargin: true, zeroline: false, showline: false, ticks: 'inside'}
    y_axis = {anchor: "x", title: y_axis_label, showgrid:false, showexponent: 'last', exponentformat: 'power', automargin: true, showline: true, ticks: 'inside'}

    if(graph_settings != null && graph_settings.axis_units_changed == true){
        x_axis.range = [ranges['x_range'][0]-(ranges['x_range'][1]-ranges['x_range'][0])/10.0   ,  ranges['x_range'][1]+(ranges['x_range'][1]-ranges['x_range'][0])/10.0 ]
        y_axis.range = ranges['y_range']
    }

    //var height = 0.5*document.documentElement.clientHeight
    var viewportheight = window.innerHeight
    var height = parseInt(0.5*viewportheight)

    var layout = {
        showlegend: true,
        dragmode: "pan",
        hovermode: "x",
        //hovermode:'closest',
        //hoverlabel: {bgcolor:"white",font_size:100,font_family:"Rockwell",width:500},
        hoverlabel: {bgcolor:"white", bordercolor: "black", align: "left", font:{font_family:"Rockwell", size:20, color:"black"}},
        //hoverdistance: 100,
        //transition : {'duration': 500},
        //margin:{"l": 0, "r": 0, "t": 100, "b": 40},
        //margin:{"l": 0, "r": 0, "t": 100, "b": 40},
        margin:{"l": 80, "r": 0, "t": 60, 'b':0},
        //xaxis:{showgrid:false, showline:false, zeroline:false},
        //yaxis:{showgrid:false, showline:false, zeroline:false},
        //width: map_width,
        //height: height,
        //height:height,
        //title:{text: "SpecViewer", y: 0.9, x: 0.5, xanchor: 'center', yanchor: 'top'},
        //title: {font: {size: 30}, text: "SpecViewer", y: 0.9, x: 0.5, xanchor: "center", yanchor: "top"},
        font: {family: "Courier New, monospace", size: 18, color: "#7f7f7f"},
        xaxis: x_axis,
        yaxis: y_axis,
        //xaxis_title:x_axis_label, yaxis_title:y_axis_label,
        font:{family:"Courier New, monospace", size:12, color:"black"},
        plot_bgcolor:'rgb(255,255,255)',
        clickmode:'event+select',
        shapes: shapes,
        annotations: annotations,
        uirevision: true,
        legend: legend,
    }
    return layout
}




function read_spectral_lines_list(){
    // read text from URL location
    var request = new XMLHttpRequest();
    request.open('GET', '/assets/spectral_lines.json', true);
    request.send(null);
    request.onreadystatechange = function () {
        if (request.readyState === 4 && request.status === 200) {
            var type = request.getResponseHeader('Content-Type');
            if (type.indexOf("text") !== 1) {
                return request.responseText;
            }
        }
    }
}


function add_alpha_to_rgb(rgb_string, alpha){
    var rgb = rgb_string.replace(/[^\d,]/g, '').split(',');
    return "rgb("+rgb[0]+","+rgb[1]+","+rgb[2]+","+alpha+")"


}


function fnu_to_abmag(fnu){
    if(fnu <= 0)
        return null
    else
        return -2.5 * Math.log10(fnu) - 48.60
}

function flambda_to_fnu(flam, lam, wavelength_unit){
    if(wavelength_unit == "nanometer")
        lam = lam * 10.0
    return (10**-23) * 3.33564095 * (10**4) * (lam**2) * flam
}

function flambda_to_abmag(flam,lam, wavelength_unit){
    return fnu_to_abmag(flambda_to_fnu(flam,lam,wavelength_unit))
}

function parse_color(input) {
    var m = input.match(/^rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$/i);
    return [parseInt(m[1]),parseInt(m[2]),parseInt(m[3])];
}

function get_curve_index_mapping(data){
    curve_mapping = {}
    if(data != null){
        trace_names = Object.keys(data['traces'])
        index = 0
        for(trace_name in data['traces']){
            if(data['traces'][trace_name].is_visible == true){
                curve_mapping[index] = trace_name
                index++
            }
        }
    }
    return curve_mapping
}


function build_traces_table(data){

    let table_rows = []
    let column_names = []
    let style_data_conditional = []
    if(data != null){
        column_names.push({id:'rank',name:'rank', hideable: true, 'editable':false, type:'numeric'})
        column_names.push({id:'name',name:'name', hideable: true, 'editable':true})
        column_names.push({id:'is_visible',name:'is_visible', hideable: true, 'editable':true})
        column_names.push({id:'ancestors',name:'ancestors', hideable: true, 'editable':false})
        column_names.push({id:'color',name:'color', hideable: true, 'editable':true})
        column_names.push({id:'linewidth',name:'linewidth', hideable: true, 'editable':true})
        column_names.push({id:'type',name:'type', hideable: true, 'editable':false})
        column_names.push({id:'catalog',name:'catalog', hideable: true, 'editable':false})

        rank = 0
        for(trace_name in data['traces']){
            trace = data['traces'][trace_name]
            if(typeof trace.is_visible == 'string'){
                trace.is_visible = (trace.is_visible == 'true')
            }
            if(trace.linewidth != null){
                if(Number.isFinite(trace.linewidth))
                    linewidth = trace.linewidth
                else
                    linewidth = trace.linewidth[0]
            }else{
                linewidth = Number.isFinite
            }

            row = {'rank':rank, 'name':String(trace_name), 'is_visible':trace.is_visible, 'ancestors':String(trace.ancestors), 'linewidth':linewidth,
                   'color':String(trace.color), 'type':String(trace.spectrum_type), 'catalog':String(trace.catalog)}

            table_rows.push(row)

            condition = {if:{column_id:'color',row_index:rank},color:String(trace.color)}

            style_data_conditional.push(condition)
            condition = {if:{column_id:'color',row_index:rank, state: "active"},color:String(trace.color),backgroundColor: String(trace.color),border: "0px solid " + String(trace.color)}
            style_data_conditional.push(condition)

            //row_tooltip = {...row}
            //Object.keys(row_tooltip).map(function(key, index) {row_tooltip[key] = String(row_tooltip[key]);});
            //tooltip_rows.push(row_tooltip)
            rank = rank+1
        }
    }
    return table = {table_rows:table_rows,column_names:column_names,style_data_conditional:style_data_conditional}
}

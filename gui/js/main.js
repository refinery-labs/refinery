var API_SERVER = location.origin.toString() + ":7777";
var ATC_SERVER = "http://100.115.92.205:1337";

var DEFAULT_LAMBDA_CODE = {
	"python2.7": `
"""
Embedded magic

Refinery memory:
	Config memory: cmemory.get( "api_key" )
	Global memory: gmemory.get( "example" )
	Force no-namespace: gmemory.get( "example", raw=True )

SQS message body:
	First message: sqs_data = json.loads( lambda_input[ "Records" ][0][ "body" ] )
"""

def main( lambda_input, context ):
    return False
`,
	"nodejs8.10": `
/*
 * Embedded magic
 */
async function main( lambda_input, context ) {
	return false;
}
`
}

var GRAPH_ICONS_ARRAY = [
	{
		"url": "/img/code-icon.png",
		"id": "lambda"
	},
	{
		"url": "/img/sqs_queue.png",
		"id": "sqs_queue"
	},
	{
		"url": "/img/clock-icon.png",
		"id": "schedule_trigger"
	}
];
var IMAGE_NODE_SPACES = "            ";

window.define = ace.define;
window.require = ace.require;

var beforeUnloadMessage = null;

var resizeEvent = new Event("paneresize");
Split(['.left-panel', '#graph'], {
  sizes: [25, 75],
  onDragEnd: function() {
    var svgOutput = document.getElementById("svg_output");
    if (svgOutput != null) {
      svgOutput.dispatchEvent(resizeEvent);
    }
  }
});

var parser = new DOMParser();
var worker;
var result;

function update_graph() {
	return new Promise(function(resolve, reject) {
		if (worker) {
			worker.terminate();
		}
		
		document.querySelector("#output").classList.add("working");
		document.querySelector("#output").classList.remove("error");
		
		worker = new Worker("./js/worker.js");
		
		worker.onmessage = function(e) {
			document.querySelector("#output").classList.remove("working");
			document.querySelector("#output").classList.remove("error");
			
			result = e.data;
			
			update_graph_output( resolve, reject );
		}
		
		worker.onerror = function(e) {
			document.querySelector("#output").classList.remove("working");
			document.querySelector("#output").classList.add("error");
			
			var message = e.message === undefined ? "An error occurred while processing the graph input." : e.message;
			
			var error = document.querySelector("#error");
			while (error.firstChild) {
			error.removeChild(error.firstChild);
		}
		
		document.querySelector("#error").appendChild(document.createTextNode(message));
		
		console.error(e);
		e.preventDefault();
		}
		
		var params = {
			src: app.graphiz_content,
			options: {
				engine: "dot",
				format: "svg"
			}
		};
		
		// Instead of asking for png-image-element directly, which we can't do in a worker,
		// ask for SVG and convert when updating the output.
		
		if (params.options.format == "png-image-element") {
			params.options.format = "svg";
		}
		
		worker.postMessage(params);
	});
}

function update_graph_output( resolve, reject ) {
	var graph = document.querySelector("#output");
	
	var svg = graph.querySelector("svg");
	if (svg) {
		graph.removeChild(svg);
	}
	
	var text = graph.querySelector("#text");
	if (text) {
		graph.removeChild(text);
	}
	
	var img = graph.querySelector("img");
	if (img) {
		graph.removeChild(img);
	}
	
	if (!result) {
		return reject();
	}
	
	var svg = parser.parseFromString(result, "image/svg+xml").documentElement;
	svg.id = "svg_output";

	// Adds in images resources for use in nodes
	var defs_element = document.createElementNS( "http://www.w3.org/2000/svg", "defs" );
	GRAPH_ICONS_ARRAY.map(function( graph_icon_data ) {
		var pattern_elem = document.createElementNS( "http://www.w3.org/2000/svg", "pattern" );
		pattern_elem.setAttribute( "id", graph_icon_data.id );
		var image_elem = document.createElementNS( "http://www.w3.org/2000/svg", "image" );
		pattern_elem.appendChild( image_elem );
		defs_element.appendChild( pattern_elem );
		var selected_pattern_elem = defs_element.querySelector( "pattern[id='" + graph_icon_data.id + "']" );;
		selected_pattern_elem.setAttributeNS( null, "id", graph_icon_data.id );
		selected_pattern_elem.setAttributeNS( null, "height", "100%" );
		selected_pattern_elem.setAttributeNS( null, "width", "100%" );
		// Required to set case-sensitive attributes as SVG needs
		selected_pattern_elem.setAttributeNS( null, "patternContentUnits", "objectBoundingBox" );
		var selected_image_pattern_elem = selected_pattern_elem.querySelector( "image" );
		selected_image_pattern_elem.setAttributeNS( null, "height", "1" );
		selected_image_pattern_elem.setAttributeNS( null, "width", "1" );
		selected_image_pattern_elem.setAttributeNS( null, "preserveAspectRatio", "none" );
		selected_image_pattern_elem.setAttributeNS( "http://www.w3.org/1999/xlink", "xlink:href", graph_icon_data.url );
	});
	
	svg.appendChild( defs_element );
	
	graph.appendChild(svg);
	
	panZoom = svgPanZoom(svg, {
		zoomEnabled: true,
		controlIconsEnabled: true,
		fit: true,
		center: true,
		minZoom: 0.1
	});
	
	svg.addEventListener('paneresize', function(e) {
		panZoom.resize();
	}, false);
	window.addEventListener('resize', function(e) {
		panZoom.resize();
	});
	
	resolve();
}

window.addEventListener("beforeunload", function(e) {
  return beforeUnloadMessage;
});

function get_graph_dom_element() {
	return document.getElementById( "output" ).querySelector( "svg" );
}

function get_graph_node( node_id ) {
	var graph_ref = get_graph_dom_element();
	var title_tags = graph_ref.querySelectorAll( "title" );
	var match_element = false;
	for( var i = 0; i < title_tags.length; i++ ) {
		if( title_tags[i].innerHTML == node_id ) {
			match_element = title_tags[i];
			break;
		}
	}
	
	if( !match_element )
		return false
	
	return match_element.parentElement;
}

function get_uuid() {
	return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
		(c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
	)
}

function get_random_node_id() {
	return "n" + get_uuid().replace( /-/g, "" ); // Must start with letter for Graphiz
}

function get_lambda_data() {
	var return_data = {};
	return_data[ "id" ] = get_random_node_id();
	return_data[ "name" ] = app.lambda_name;
	return_data[ "language" ] = app.lambda_language;
	return_data[ "code" ] = app.lambda_code;
	return_data[ "memory" ] = app.lambda_memory;
	return_data[ "libraries" ] = app.lambda_libraries;
	return_data[ "max_execution_time" ] = app.lambda_max_execution_time;
	return_data[ "type" ] = "lambda";
	return return_data
}

function get_node_data_by_id( node_id ) {
	var results = app.workflow_states.filter(function( workflow_state ) {
		return workflow_state[ "id" ] === node_id;
	});
	if( results.length > 0 ) {
		return results[0];
	}
	return false;
}

function get_state_transition_by_id( transition_id ) {
	var results = app.workflow_relationships.filter(function( workflow_relationship ) {
		return workflow_relationship[ "id" ] === transition_id;
	});
	if( results.length > 0 ) {
		return results[0];
	}
	return false;
}

function get_element_from_string( input_string ) {
	var div = document.createElement( "div" );
	div.innerHTML = input_string.trim();
	return div.firstChild;
}

function get_escaped_html( input_html ) {
	var char_map = {
		'&': '&amp;',
		'<': '&lt;',
		'>': '&gt;',
		'"': '&quot;',
		"'": '&#39;',
		'/': '&#x2F;',
		'`': '&#x60;',
		'=': '&#x3D;'
	};
	
	return String( input_html ).replace(/[&<>"'`=\/]/g, function (s) {
		return char_map[s];
	});
}

function build_dot_graph() {
	var dot_contents = "digraph \"renderedworkflow\"{\n";
	
	app.workflow_states.map(function( workflow_state ) {
		// Node that the shape "square" is reserved for image icons

		// Defaults
		var node_properties = {
			"href": "javascript:select_node('" + workflow_state["id"] + "')",
			"label": workflow_state["name"],
			"fillcolor": "#ff7f00",
			"style": "filled",
			"shape": "rect",
			"fontname": "Courier",
			"fontsize": "10",
			"color": "#000000",
		};
		
		if( workflow_state["id"] == app.selected_node ) {
			// If it's a selected node turn it yellow, make a red border
			node_properties.fillcolor = "#fffa00";
			node_properties.color = "#ff0000";
			node_properties.penwidth = "4";
		} else if ( workflow_state["type"] == "sfn_start" || workflow_state["type"] == "sfn_end" ) {
			// Start or End special node
			node_properties.fillcolor = "#ff9900";
		}
		
		var picture_node_types = GRAPH_ICONS_ARRAY.map(function( graph_item ) {
			return graph_item.id;
		});
		
		if( workflow_state[ "type" ] == "sfn_start" ) {
			node_properties.shape = "circle";
		} else if ( workflow_state[ "type" ] == "sfn_end" ) {
			node_properties.shape = "octagon";
		} else if ( picture_node_types.includes( workflow_state[ "type" ] ) ) {
			node_properties.shape = "square";
		}
		
		// We will super impose the label at a later time
		if( node_properties.shape === "square" ) {
			node_properties.label = IMAGE_NODE_SPACES;
			delete node_properties.style;
			delete node_properties.fillcolor;
			node_properties.fill = "none";
			
			if( !( workflow_state["id"] == app.selected_node ) ) {
				node_properties.style = "setlinewidth(0)";
				node_properties.stroke = "none";
			}
			
			node_properties.tooltip = btoa(JSON.stringify({
				"name": workflow_state["name"],
				"type": workflow_state["type"]
			}));
		}
		
		// Dynamically create the .dot line
		var new_dot_line = "\t" + workflow_state["id"] + "[ ";
		var attributes_array = [];
		for ( var key in node_properties ) {
			if ( node_properties.hasOwnProperty( key ) ) {
				attributes_array.push(
					key + "=\"" + node_properties[ key ] + "\""
				);
			}
		}
		
		new_dot_line += attributes_array.join( ", " );
		new_dot_line += " ];\n";
		
		dot_contents += new_dot_line;
	});
	
	app.workflow_relationships.map(function( workflow_relationship ) {
		dot_contents += "\t" + workflow_relationship["node"] + " -> " + workflow_relationship["next"];
		
		// "next" text next to transition
		dot_contents += " [penwidth=2, label=<<table cellpadding=\"10\" border=\"0\" cellborder=\"0\"><tr><td>" + get_escaped_html( workflow_relationship[ "name" ] ) + "</td></tr></table>> href=\"javascript:select_transition('" + workflow_relationship[ "id" ] + "')\" ";
		
		if( workflow_relationship.id == app.selected_transition ) {
			dot_contents += "color=\"#ff0000\"";
		} else {
			dot_contents += "color=\"#000000\"";
		}
		
		dot_contents += "]\n"
	});
	
	dot_contents += "}";
	app.graphiz_content = dot_contents;
	
	// After we've drawn the chart we do our custom injections
	update_graph().then(function() {
		var svg_nodes = document.querySelectorAll( "g" );
	
		for( var i = 0; i < svg_nodes.length; i++ ) {
			var text_element = svg_nodes[i].querySelector( "text" );
			if( text_element == null ) {
				continue;
			}
			
			var a_elem = text_element.parentNode;
			
			var polygon = a_elem.querySelector( "polygon" );
			var title_text = a_elem.getAttribute( "xlink:title" );
			
			// Try to base64 decode and JSON decode
			try {
				var title_text_data = JSON.parse( atob( title_text ) );
				a_elem.setAttribute( "xlink:title", title_text_data.name );
			} catch ( e ) {
				continue;
			}
			
			polygon.setAttribute( "fill", "url(#" + title_text_data.type + ")" );
			var poly_box = polygon.getBBox();
			
			text_element.innerHTML = title_text_data.name;
			var SVGRect = text_element.getBBox();
			var rect = document.createElementNS( "http://www.w3.org/2000/svg", "rect");
		    rect.setAttribute("x", ( SVGRect.x - 5 ) );
		    rect.setAttribute("y", ( SVGRect.y - 5 ) );
		    rect.setAttribute("width", ( SVGRect.width + 10 ) );
		    rect.setAttribute("height", ( SVGRect.height + 10 ) );
		    //rect.setAttribute("fill", "black");
		    rect.setAttribute("style", "fill:black;fill-opacity:0.7;");
		    text_element.setAttributeNS( null, "fill", "#FFFFFF" );
		    text_element.parentNode.insertBefore( rect, text_element );
		}
	});
}

/*
	Calculates the possible next state transitions
	to narrow down what the user can select.
	
	e.g. prevents duplicate state transitions
*/
function get_variable_state_transitions() {
	var potential_next_states = app.workflow_states;
	
	// Next state can't be itself (infinite loop)
	potential_next_states = potential_next_states.filter(function( next_state ) {
		return next_state.id != app.selected_node;
	});
	
	return potential_next_states;
}

function select_node( node_id ) {
	// Set selected node ID
	app.selected_node = node_id;

	var selected_node_data = get_node_data_by_id(
		app.selected_node
	);
	
	// Navigate to corresponding page
	if( selected_node_data.type == "lambda" ) {
		// Set up Lambda state for editor
		reset_current_lambda_state_to_defaults();
		app.lambda_name = selected_node_data.name;
		app.lambda_language = selected_node_data.language;
		app.unformatted_libraries = selected_node_data.libraries.join( "\n" );
		app.lambda_code = selected_node_data.code;
		app.lambda_memory = selected_node_data.memory;
		app.lambda_max_execution_time = selected_node_data.max_execution_time;
		app.navigate_page( "modify-lambda" );
	} else if( selected_node_data.type == "sqs_queue" ) {
		reset_current_sqs_queue_state_to_defaults();
	    var sqs_trigger_data = {
			"queue_name": selected_node_data.name,
			"content_based_deduplication": selected_node_data.content_based_deduplication,
			"batch_size": selected_node_data.batch_size,
			"sqs_job_template": selected_node_data.sqs_job_template
	    };
	    Vue.set( app, "sqs_trigger_data", sqs_trigger_data );
	    
		app.navigate_page( "modify-sqs_queue" );
	} else if ( selected_node_data.type == "schedule_trigger" ) {
		reset_current_schedule_trigger_to_defaults();
		
		var trigger_data = {
            "name": selected_node_data.name,
			"schedule_expression": selected_node_data.schedule_expression,
			"description": selected_node_data.description,
			"unformatted_input_data": selected_node_data.unformatted_input_data,
			"input_dict": selected_node_data.input_dict,
		}

	    Vue.set( app, "scheduled_trigger_data", trigger_data );
	    
	    app.navigate_page( "modify-schedule_trigger" );
	} else {
		alert( "Error, unrecognized node type!" );
	}
	
	// Can't have both selected
	if( app.selected_transition ) {
		app.selected_transition = false;
	}
}

function select_transition( transition_id ) {
	if( app.selected_transition == transition_id ) {
		app.selected_transition = false;
	} else {
		app.selected_transition = transition_id;
	}
	
	// Can't have both selected
	if( app.selected_node ) {
		app.selected_node = false;
	}
	
	if( app.selected_transition ) {
		// Load transition data into current
		var selected_transition_data = app.selected_transition_data;
		Vue.set( app, "state_transition_conditional_data", selected_transition_data );
		app.navigate_page( "modify-state-transition" );
	} else {
		app.navigate_page( "welcome" );
	}
	
	build_dot_graph();
}

function reset_current_schedule_trigger_to_defaults() {
    var scheduled_trigger_data = {
    	"name": "Untitled Trigger",
    	"schedule_expression": "rate(1 minute)",
    	"description": "Example scheduled rule description.",
    	"input_dict": {},
    	"unformatted_input_data": "{}",
    }
    Vue.set( app, "scheduled_trigger_data", scheduled_trigger_data );
}

function reset_current_sqs_queue_state_to_defaults() {
    var sqs_trigger_data = {
		"queue_name": app.lambda_name,
		"content_based_deduplication": true,
		"batch_size": 1,
		"sqs_job_template": JSON.stringify({
			"id": "1"
		}, false, 4 ),
    }
    Vue.set( app, "sqs_trigger_data", sqs_trigger_data );
}

function reset_current_lambda_state_to_defaults() {
	app.lambda_name = "";
	app.lambda_language = "python2.7";
	//app.lambda_libraries = [];
	app.unformatted_libraries = "";
	app.lambda_code = DEFAULT_LAMBDA_CODE[ "python2.7" ];
}

function get_project_json() {
	return JSON.stringify({
		"version": "1.0.0",
		"name": app.project_name,
		"workflow_states": app.workflow_states,
		"workflow_relationships": app.workflow_relationships,
	}, false, 4 );
}

function download_file( file_contents, filename, content_type ) {
    if( !content_type ) {
    	content_type = "application/octet-stream";
    }
    var a = document.createElement( "a" );
    var blob = new Blob(
    	[file_contents],
    	{"type": content_type}
    );
    a.href = window.URL.createObjectURL( blob );
    a.download = filename;
    a.click();
}

function get_safe_name( input_string ) {
	return input_string.replace(
		/[^a-z0-9\-\_]/gi,
		"_"
	);
}

function import_project_data( input_project_data ) {
	app.project_name = input_project_data[ "name" ];
	Vue.set( app, "workflow_states", input_project_data[ "workflow_states" ] );
	Vue.set( app, "workflow_relationships", input_project_data[ "workflow_relationships" ] );
	build_dot_graph();
}

function project_file_uploaded( event_data ) {
	var file_data = event_data.target.files[0];
	var reader = new FileReader();
	reader.onload = function() {
		var file_contents = reader.result;
		try {
			import_project_data(
				JSON.parse(
					file_contents
				)
			);
		} catch ( e ) {
			alert( "Error parsing project data! Invalid JSON?" );
			console.log( e );
		}
	}
	reader.readAsText( file_data );
}

function delete_atc_queue_loader_by_id( queue_loader_id ) {
	return atc_api_request(
		"DELETE",
		"api/v1/queue_loaders",
		{
			"id": queue_loader_id
		}
	).then(function( results ) {
		return results.id;
	})
}

function get_atc_queue_loaders() {
	return atc_api_request(
		"GET",
		"api/v1/queue_loaders",
		{}
	).then(function( results ) {
		return results.queue_loaders;
	})
}

function get_atc_iterators() {
	return atc_api_request(
		"GET",
		"api/v1/iterators",
		{}
	).then(function( results ) {
		return results.iterators;
	})
}

function get_atc_sqs_queues() {
	return atc_api_request(
		"GET",
		"api/v1/queues",
		{}
	).then(function( results ) {
		return results.queues;
	})
}

function create_queue_loader( queue_name, job_template, options, iterators_options_array ) {
	return atc_api_request(
		"POST",
		"api/v1/queue_loaders/cron",
		{
			"queue_name": queue_name,
			"job_template": job_template,
			"options": options,
			"iterators_options_array": iterators_options_array,
		}
	);
}

function get_job_template( queue_name ) {
	return api_request(
		"POST",
		"api/v1/sqs/job_template/get",
		{
			"queue_name": queue_name
		}
	).then(function( response ) {
		return response.job_template;
	});
}

function save_job_template( queue_name, job_template_data_string ) {
	return api_request(
		"POST",
		"api/v1/sqs/job_template",
		{
			"queue_name": queue_name,
			"job_template": job_template_data_string,
		}
	).then(function( response ) {
		return response.id;
	})
}

function delete_saved_function( id ) {
	return api_request(
		"DELETE",
		"api/v1/functions/delete",
		{
			"id": id,
		}
	);
}

function search_saved_functions( query ) {
	return api_request(
		"POST",
		"api/v1/functions/search",
		{
			"query": query,
		}
	);
}

function update_saved_function( id, name, description, code, language, libraries ) {
	return api_request(
		"POST",
		"api/v1/functions/update",
		{
			"id": id,
			"name": name,
			"description": description,
			"code": code,
			"language": language,
			"libraries": libraries,
		}
	);
}

function create_saved_function( name, description, code, language, libraries ) {
	return api_request(
		"POST",
		"api/v1/functions/create",
		{
			"name": name,
			"description": description,
			"code": code,
			"language": language,
			"libraries": libraries,
		}
	);
}

function deploy_lambda( name, language, code, libraries, memory, max_execution_time ) {
	return api_request(
		"POST",
		"api/v1/aws/deploy_lambda",
		{
			"name": name,
			"language": language,
			"code": code,
			"libraries": libraries,
			"memory": parseInt( memory ),
			"max_execution_time": parseInt( max_execution_time )
		}
	);
}

function run_tmp_lambda( language, code, libraries, memory, max_execution_time ) {
	return api_request(
		"POST",
		"api/v1/aws/run_tmp_lambda",
		{
			"language": language,
			"code": code,
			"libraries": libraries,
			"memory": parseInt( memory ),
			"max_execution_time": parseInt( max_execution_time )
		}
	);
}

function create_schedule_trigger( name, schedule_expression, description, target_type, target_id, target_arn, input_dict ) {
	return api_request(
		"POST",
		"api/v1/aws/create_schedule_trigger",
		{
			"name": name,
			"schedule_expression": schedule_expression,
			"description": description,
			"target_type": target_type,
			"target_arn": target_arn,
			"target_id": target_id,
			"input_dict": input_dict
		}
	);
}

function deploy_infrastructure( diagram_data ) {
	return api_request(
		"POST",
		"api/v1/aws/deploy_diagram",
		{
			"diagram_data": diagram_data,
		}
	);
}

/*
    Make API request
*/
function api_request( method, endpoint, body ) {
    return http_request(
        method,
        API_SERVER + "/" + endpoint,
        [
            {
                "key": "Content-Type",
                "value": "application/json",
            },
            {
                "key": "X-CSRF-Validation-Header",
                "value": "true"
            }
        ],
        JSON.stringify(
            body
        )
    ).then(function( response_text ) {
    	var response_data = JSON.parse(
    		response_text
    	);
    	
    	// If we get a redirect in the response, redirect instead of returning
    	if( "redirect" in response_data && response_data[ "redirect" ] != "" ) {
    		window.location = response_data[ "redirect" ];
    	}
    	
    	if( "success" in response_data && response_data[ "success" ] == false ) {
    		return Promise.reject( response_data );
    	} else {
    		return response_data;
    	}
    });
}

/*
    Make ATC API request
*/
function atc_api_request( method, endpoint, body ) {
    return http_request(
        method,
        ATC_SERVER + "/" + endpoint,
        [
            {
                "key": "Content-Type",
                "value": "application/json",
            },
            {
                "key": "X-Server-Secret",
                "value": "SOMETHING_PRETTY_OBSCURE_I_GUESS" // TODO make this dynamic
            }
        ],
        JSON.stringify(
            body
        )
    ).then(function( response_text ) {
    	var response_data = JSON.parse(
    		response_text
    	);
    	
    	// If we get a redirect in the response, redirect instead of returning
    	if( "redirect" in response_data && response_data[ "redirect" ] != "" ) {
    		window.location = response_data[ "redirect" ];
    	}
    	
    	if( "success" in response_data && response_data[ "success" ] == false ) {
    		return Promise.reject( response_data );
    	} else {
    		return response_data.results;
    	}
    });
}

ace.config.set( "basePath", "./js/" );
Vue.component( "Editor", {
    template: '<div :id="editorId" style="width: 100%; height: 100%;"></div>',
    props: ['editorId', 'content', 'lang', 'theme'],
    data() {
        return {
            editor: Object,
            beforeContent: false,
        }
    },
    watch: {
        "content" (value) {
        	if( value !== this.beforeContent ) {
        		this.editor.setValue( value, 1 );
        	}
        },
        "lang" (lang) {
            this.editor.getSession().setMode({
                path: `ace/mode/${lang}`,
                v: Date.now()
            });
        }
    },
    mounted() {
        var lang = this.lang || 'python'
        var theme = this.theme || 'monokai'

        this.editor = window.ace.edit(this.editorId)
        this.editor.setValue(this.content, 1)

        this.editor.getSession().setMode({
            path: `ace/mode/${lang}`,
            v: Date.now()
        });
        this.editor.setTheme(`ace/theme/${theme}`)

        this.editor.on('change', () => {
        	this.beforeContent = this.editor.getValue();
            this.$emit(
                'change-content',
                this.editor.getValue()
            )
            this.$emit(
                'change-content-context', {
                    "value": this.editor.getValue(),
                    "this": this
                }
            )
        })
    }
})

/*
    Make HTTP request
*/
function http_request( method, uri, headers, body ) {
    return new Promise(function(resolve, reject) {
        var http = new XMLHttpRequest();
        http.open(
            method,
            uri,
            true
        );
        http.withCredentials = true;
    
        for( var i = 0; i < headers.length; i++ ) {
            http.setRequestHeader(
                headers[i][ "key" ],
                headers[i][ "value" ]
            );
        }
        
        http.onreadystatechange = function() {//Call a function when the state changes.
            if( http.readyState == 4 ) {
                resolve(
                    http.responseText
                );
            }
        }
        
        if( !body || body == "" ) {
            body = false;
        }
        
        http.send( body );
    });
}

// On resize redraw graph
$(window).resize(function(){
    build_dot_graph();
});

// On load
$( document ).ready(function() {
	document.getElementById( "project_file_upload" ).addEventListener(
		"change",
		project_file_uploaded,
		false
	);
});

var app = new Vue({
	el: "#app",
    components:{
        //"vue-ace-editor": VueAceEditor
    },
	data: {
		page: "welcome",
		selected_node: false,
		selected_node_state: false,
		selected_transition: false,
	    "workflow_states": [
	        {
	            "id": "n517c182f855849bab13434d8381c9c61",
	            "name": "Return Some Data",
	            "language": "python2.7",
	            "libraries": [],
	            "code": "def main( lambda_input, context ):\n    return {\n        \"test\": \"worked!\"\n    }\n",
	            "memory": 128,
	            "max_execution_time": 60,
	            "type": "lambda"
	        },
	        {
	            "id": "n9264e4fe12dc44b5a2e41e811e39ad2c",
	            "name": "Write Return to S3",
	            "language": "python2.7",
	            "libraries": [
	                "boto3"
	            ],
	            "code": "import boto3\nimport json\n\ndef main( lambda_input, context ):\n    write_to_s3(\n        \"lambdatestbucketpewpew\",\n        \"output\",\n        json.dumps( lambda_input )\n    )\n    return True\n\n# Store in S3 \ndef write_to_s3( bucket_name, object_key, body ):\n\timport boto3\n\ts3_client = boto3.client( \"s3\" )\n\tresult = s3_client.put_object(\n\t\tBucket=bucket_name,\n\t\tKey=object_key,\n\t\tBody=body\n\t)\n\treturn result",
	            "memory": 128,
	            "max_execution_time": 60,
	            "type": "lambda"
	        }
	    ],
	    "workflow_relationships": [
	        {
	            "id": "n047f72ec029c49739a62e566eb164625",
	            "name": "if True",
	            "type": "if",
	            "expression": "True",
	            "node": "n517c182f855849bab13434d8381c9c61",
	            "next": "n9264e4fe12dc44b5a2e41e811e39ad2c"
	        }
	    ],
	    ace_language_to_lang_id_map: {
	    	"python2.7": "python",
	    	"nodejs8.10": "javascript"
	    },
	    node_types_with_simple_transitions: [
	    	"schedule_trigger",
	    	"sqs_queue"
	    ],
	    available_transition_types: [
	    	"then",
	    	"if",
	    	"else",
	    	"exception"
	    ],
		state_transition_conditional_data: {
			"name": "then",
			// "then", "if", "else", "exception"
			"type": "then",
			"expression": "",
			"node": "",
			"next": false,
		},
		graphiz_content: "",
		// Project name
		project_name: "Untitled Project",
		// Currently selected lambda name
		lambda_name: "",
		// Currently selected lambda language
		lambda_language: "python2.7",
		// Currently selected lambda imports
		unformatted_libraries: "",
		// lambda_libraries: [], This is now computed!
		// Currently selected lambda code
        lambda_code: "",
        // Currently selected lambda max memory
        lambda_memory: 128,
        // Currently selected lambda max runtime
        lambda_max_execution_time: 30,
        // The result of a lambda execution
        lambda_exec_result: false,
        // Lambda build timer
        lambda_build_time: 0,
    	// Target data for when a schedule-based trigger is created
        scheduled_trigger_data: {
        	"name": "Scheduled_Trigger_Example",
        	"schedule_expression": "rate(1 minute)",
        	"description": "Example scheduled rule description.",
        	"unformatted_input_data": "{}",
        	"input_dict": {},
        },
        // Target data for when an SQS-based trigger is created
        sqs_trigger_data: {
			"queue_name": "Example Queue",
			"content_based_deduplication": true,
			"batch_size": 1,
			"sqs_job_template": JSON.stringify({
				"id": "1"
			}, false, 4 ),
        },
        // Whether the lambda deploy is loading
        lambda_deploy_loading: true,
        // Deployed Lambda link
        lambda_deployed_link: "",
        // Status text while deploying lambda
        lambda_deploy_status_text: "Loading",
        // All project data serialized as JSON for export
        project_data_json: "",
        // Errors while pasting JSON in import project menu
        import_paste_error: false,
        // Data for saving new function
        saved_function_data: {
        	"id": "",
			"name": "",
			"description": "",
			"code": "",
			"language": "python2.7",
			"libraries": [],
        },
        // Unformatted saved function imports
		unformatted_saved_function_libraries: "",
        // Search results for saved function search
        saved_function_search_results: [],
        // Search term for saved function search
        saved_function_search_query: "",
        
        // Whether the infrastructure is still being deployed.
        deploying_infrastructure: false,
        
        // Time taken to deploy infrastructure
        deploy_infrastructure_time: 0,
        
        // Refinery ATC
        atc: {
        	// SQS queues
        	sqs_queues: [],
        	// Cron loader
			queue_loader: {
				"queue_name": "example",
				"job_template": {
					"id": "iterator_value",
				},
				"options": {
					"method_type": "cron",
					"method_data": {
						"expression": "* * * * * *"
					},
					"cycles": 10,
				},
				"iterators_options_array": [
					{
						"type": "primary",
						"template_key": "id",
						"arguments": [ 0, 100, 1, "000" ],
						"iterator_function": "number_range"
					}
				]
			},
			unformatted_job_template_text: "",
			iterators: [],
			running_queue_loaders: [],
        },
        
        codeoptions: {
            mode: "python",
            theme: "monokai",
            fontSize: 12,
            fontFamily: "monospace",
            highlightActiveLine: true,
            highlightGutterLine: false
        },
	},
	watch: {
		saved_function_search_query: function( value, previous_value ) {
			app.search_saved_functions( value );
		},
		"atc.queue_loader.options.method_data.expression": function( value, previous_value ) {
			if( value.toLocaleLowerCase() === "immediate" ) {
				app.atc.queue_loader.options.method_type = "immediate";
			} else {
				app.atc.queue_loader.options.method_type = "cron";
			}
		},
		"atc.queue_loader.queue_name": function( value, previous_value ) {
			get_job_template( value ).then(function( job_template_string ) {
				// Format it
				app.atc.unformatted_job_template_text = JSON.stringify(
					JSON.parse( job_template_string ),
					false,
					4
				);
			});
		},
		
		// Automatically update the graph when the state has changed
		workflow_states: function( value, previous_value ) {
			build_dot_graph();
		},
		workflow_relationships: function( value, previous_value ) {
			build_dot_graph();
		},
		selected_transition: function( value, previous_value ) {
			build_dot_graph();
		},
		selected_node: function( value, previous_value ) {
			build_dot_graph();
		},
		selected_transition: function( value, previous_value ) {
			build_dot_graph();
		}
	},
	computed: {
		lambda_libraries: {
			cache: false,
			get() {
				var new_value = app.unformatted_libraries.trim();
				if( new_value == "" ) {
					return [];
				}
				
				return new_value.split( "\n" );
			}
		},
		selected_node_data: function() {
			return get_node_data_by_id( app.selected_node );
		},
		selected_transition_data: function() {
			return get_state_transition_by_id( app.selected_transition );
		},
		selected_transition_start_node: function() {
			if( app.selected_node_data ) {
				return app.selected_node_data;
			}
			var transition_data = get_state_transition_by_id( app.selected_transition );
			var origin_node_data = get_node_data_by_id( transition_data.node );
			return origin_node_data;
		},
		valid_transition_paths: function() {
			var valid_paths = [];
			var start_node_id = app.selected_node_data.id;
			
			if( !start_node_id ) {
				start_node_id = app.selected_transition_data.node;
			}

			app.workflow_states.map(function( workflow_state ) {
				if( app.is_valid_transition_path( start_node_id, workflow_state.id ) ) {
					valid_paths.push( workflow_state );
				}
			});
			
			return valid_paths;
		}
	},
	methods: {
		is_simple_transition: function() {
			if( app.selected_node_data ) {
				return app.node_types_with_simple_transitions.includes( app.selected_node_data.type );
			} else if ( app.selected_transition_start_node ) {
				return app.node_types_with_simple_transitions.includes( app.selected_transition_start_node.type );
			}
		},
		duplicate_lambda: function() {
			// Copy selected Lambda
			var lambda_copy = JSON.parse( JSON.stringify( app.selected_node_data ) );
			// Generate new node ID
			lambda_copy[ "id" ] = get_random_node_id();
			
			// Add to master diagram
			app.workflow_states.push( lambda_copy );
		},
		lambda_language_manual_change: function() {
			app.unformatted_libraries = "";
			app.lambda_code = DEFAULT_LAMBDA_CODE[ app.lambda_language ];
		},
		deploy_infrastructure: async function() {
			// Set that we're deploying the infrastructure
			app.deploying_infrastructure = true;
			
			// Reset deployment timer
			app.deploy_infrastructure_time = 0;
			
			// Start timer for deployment
			var start_time = Date.now();
			
			$( "#deploydiagram_output" ).modal(
				"show"
			);
			
			var results = await deploy_infrastructure(
				get_project_json()
			);
			
			console.log( "Infrastructure deployment result: " );
			console.log(
				JSON.stringify(
					results,
					false,
					4
				)
			);
			
			var delta = Date.now() - start_time;
			app.deploy_infrastructure_time = ( delta / 1000 );
			
			// Mark that we're done
			app.deploying_infrastructure = false;
		},
		is_valid_transition_path: function( first_node_id, second_node_id ) {
			var valid_type_transitions = [
				{
					"first_type": "lambda",
					"second_type": "lambda",
				},
				{
					"first_type": "sqs_queue",
					"second_type": "lambda",
				},
				{
					"first_type": "lambda",
					"second_type": "sqs_queue",
				},
				{
					"first_type": "schedule_trigger",
					"second_type": "lambda",
				}
			];
			
			// Grab data for both nodes and determine if it's possible path
			var first_node_data = get_node_data_by_id( first_node_id );
			var second_node_data = get_node_data_by_id( second_node_id );

			return valid_type_transitions.some(function( type_transition_data ) {
				// If it matches a valid transition, then set is_valid_transition to true
				return first_node_data.type == type_transition_data.first_type && second_node_data.type == type_transition_data.second_type;
			});
		},
		update_state_transition: function() {
			var updated_transition = {
				"id": app.selected_transition,
				"name": app.state_transition_conditional_data.name,
				"type": app.state_transition_conditional_data.type,
				"expression": app.state_transition_conditional_data.expression,
				"node": app.state_transition_conditional_data.node,
				"next": app.state_transition_conditional_data.next,
			}
			
			app.workflow_relationships = app.workflow_relationships.map(function( workflow_relationship ) {
				if( workflow_relationship.id == updated_transition.id ) {
					return updated_transition;
				} else {
					return workflow_relationship;
				}
			});
			
			app.selected_transition = false;
			
			app.navigate_page( "welcome" );
		},
		add_timer_trigger_node: function() {
			var new_timer_trigger = {
				"id": get_random_node_id(),
	            "name": "Untitled Timer",
	            "type": "schedule_trigger",
				"schedule_expression": "rate(1 minute)",
				"description": "Example scheduled rule description.",
				"unformatted_input_data": "{}",
				"input_dict": {},
			}
			
			app.workflow_states.push( new_timer_trigger );
		},
		add_lambda_node: function() {
			var new_lambda_data = {
				"id": get_random_node_id(),
	            "name": "Untitled Lambda",
	            "language": "python2.7",
	            "code": DEFAULT_LAMBDA_CODE[ "python2.7" ],
	            "memory": 128,
	            "libraries": [],
	            "max_execution_time": 60,
	            "type": "lambda"
			}
			
			app.workflow_states.push( new_lambda_data );
		},
		add_sqs_node: function() {
		    var sqs_queue_node_data = {
			    "id": get_random_node_id(),
			    "type": "sqs_queue",
			    "name": "Untitled Queue",
				"queue_name": "Untitled Queue",
				"content_based_deduplication": true,
				"batch_size": 1,
				"sqs_job_template": JSON.stringify({
					"id": "1"
				}, false, 4 ),
		    };
	    
			app.workflow_states.push( sqs_queue_node_data );
		},
		todo: function() {
			$( "#todo_output" ).modal(
				"show"
			);
		},
		update_sqs_job_template: function( new_value ) {
			app.sqs_trigger_data.sqs_job_template = new_value;
		},
		kill_job_loader: function( id ) {
			delete_atc_queue_loader_by_id( id ).then(function( result_id ) {
				app.view_refinery_atc();
			});
		},
		add_iterator: function( index ) {
			app.atc.queue_loader.iterators_options_array.push({
				"type": "supporting",
				"template_key": "supporting_in_memory_array",
				"arguments": [
					[ "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten" ]
				],
				"iterator_function": "in_memory_array"
			})
		},
		delete_iterator: function( index ) {
			delete app.atc.queue_loader.iterators_options_array.splice(
				index,
				1
			);
		},
		create_queue_loader: function() {
			// Todo Add a validation layer to this
			
			/*
				Slight hack to work around the way options are passed for
				"immediate" and "cron" iterators.
			*/
			var generated_options = {};
			if( app.atc.queue_loader.options.method_type === "immediate" ) {
				generated_options = {
					"method_type": "immediate",
				}
			} else {
				generated_options = app.atc.queue_loader.options;
			}
			
			create_queue_loader(
				app.atc.queue_loader.queue_name,
				app.atc.queue_loader.job_template,
				app.atc.queue_loader.options,
				app.atc.queue_loader.iterators_options_array
			).then(function() {
				app.view_refinery_atc();
			});
		},
		atc_update_arguments: function( context_object ) {
			try {
				var argument_data = JSON.parse(
					context_object.value
				);

				var index = context_object.this.$el.getAttribute( "arg_index" );
				
				app.atc.queue_loader.iterators_options_array[ index ].arguments = Object.values(
					argument_data
				);
			} catch ( e ) {
				console.log( "Error parsing arguments!" );
			}
		},
		atc_get_arguments_by_iterator_id: function( iterator_id ) {
			for( var i = 0; i < app.atc.iterators.length; i++ ) {
				if( app.atc.iterators[i].id == iterator_id ) {
					return app.atc.iterators[i].arguments;
				}
			}
		},
		atc_job_template_text_changed: function( val ) {
			// TODO
			try {
				app.atc.queue_loader.job_template = JSON.parse(
					val
				);
			} catch ( e ) {
				
			};
		},
		view_atc_create_loader: function() {
			/*
				"example",
				{
					"name": "Example Job",
				},
				{
					"method_type": "cron",
					"method_data": {
						"expression": "* * * * * *",
						"amount": 100,
					},
					"cycles": 15,
				},
				[
					{
						"type": "primary",
						"template_key": "first_primary",
						"arguments": [ 0, 50, 1, "000" ],
						"iterator_function": "number_range"
					},
					{
						"type": "supporting",
						"template_key": "supporting_in_memory_array",
						"arguments": [
							[ "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten" ]
						],
						"iterator_function": "in_memory_array"
					}
				]
			*/
			var default_loader = {
				"queue_name": "example",
				"job_template": {
					"id": "iterator_value",
				},
				"options": {
					"method_type": "cron",
					"method_data": {
						"expression": "* * * * * *"
					},
					"cycles": 10,
				},
				"iterators_options_array": [
					{
						"type": "primary",
						"template_key": "id",
						"arguments": [ 0, 100, 1, "000" ],
						"iterator_function": "number_range"
					}
				]
			}
			
			// Set queue name to first SQS queue by default
			if( app.atc.sqs_queues.length > 0 ) {
				default_loader.queue_name = app.atc.sqs_queues[0];
				get_job_template( default_loader.queue_name ).then(function( job_template_string ) {
					// Format it
					app.atc.unformatted_job_template_text = JSON.stringify(
						JSON.parse( job_template_string ),
						false,
						4
					);
				});
			} else {
				// Set job template text
				app.atc.unformatted_job_template_text = JSON.stringify(
					app.atc.queue_loader.job_template,
					false,
					4
				);
			}
			
			Vue.set( app.atc, "queue_loader", default_loader );
			
			app.navigate_page( "atc-queue-loader" );
		},
		update_refinery_atc_data: function() {
			get_atc_sqs_queues().then(function( queue_names_array ) {
				app.atc.sqs_queues = queue_names_array;
			});
			
			get_atc_iterators().then(function( iterators ) {
				app.atc.iterators = iterators;
			});
			
			get_atc_queue_loaders().then(function( queue_loaders ) {
				app.atc.running_queue_loaders = queue_loaders;
			});
		},
		view_refinery_atc: function() {
			app.navigate_page( "atc" );
			
			app.update_refinery_atc_data();
		},
		merge_saved_function: function() {
			for( var i = 0; i < app.saved_function_data.libraries.length; i++ ) {
				if( app.lambda_libraries.indexOf( app.saved_function_data.libraries[i] ) === -1 ) {
					app.lambda_libraries.push(
						app.saved_function_data.libraries[i]
					);
				}
			}
			
			if( app.saved_function_data.language == "python2.7" ) {
				app.lambda_code += "\n# " + app.saved_function_data.name + " \n" + app.saved_function_data.code.trim() + "\n";
			}
		},
		saved_function_libraries_changed: function( val ) {
			val = val.trim();
			var libraries = val.split( "\n" );
			app.saved_function_data.libraries = libraries;
		},
		delete_saved_function: function() {
			delete_saved_function(
				app.saved_function_data.id,
			)
		},
		update_saved_function: function() {
			update_saved_function(
				app.saved_function_data.id,
				app.saved_function_data.name,
				app.saved_function_data.description,
				app.saved_function_data.code,
				app.saved_function_data.language,
				app.saved_function_data.libraries
			).then(function( results ) {
				console.log( "Results" );
				console.log( results );
			});
		},
		view_saved_function: function( event ) {
			var saved_function_id = event.srcElement.getAttribute( "id" );
			
			// Get saved function with that ID
			var matched_functions = app.saved_function_search_results.filter(function( saved_function_search_result ) {
				return ( saved_function_search_result.id === saved_function_id );
			});
			
			var matched_function = matched_functions[0];
			Vue.set( app, "saved_function_data", matched_function );
			
			app.unformatted_saved_function_libraries = app.saved_function_data.libraries.join( "\n" );
			
			$( "#viewsavefunction_output" ).modal(
				"show"
			);
		},
		search_saved_functions: function( query ) {
			search_saved_functions( query ).then(function( results ) {
				app.saved_function_search_results = results[ "results" ];
			});
		},
		view_search_functions_modal: function() {
			// Clear search query
			app.saved_function_search_query = "";
			// Clear previous
			app.unformatted_saved_function_libraries = "";
			
			$( "#searchsavedfunction_output" ).modal(
				"show"
			);
		},
		saved_new_add_function: function() {
			create_saved_function(
				app.saved_function_data.name,
				app.saved_function_data.description,
				app.saved_function_data.code,
				app.saved_function_data.language,
				app.saved_function_data.libraries
			).then(function( results ) {
				console.log( "Results" );
				console.log( results );
			});
		},
		update_add_function_code: function( value ) {
			app.saved_function_data.code = value;
		},
		view_add_function_modal: function() {
	        var saved_function_data = {
				"name": "",
				"description": "",
				"code": `
def example( parameter ):
    """
    Example function, should be self-contained and documented.
    """
    return parameter.upper()
`,
				"language": "python2.7",
				"libraries": [],
	        };
	        
	        Vue.set( app, "saved_function_data", saved_function_data );
	        
			// Clear previous
			app.unformatted_saved_function_libraries = "";
	        
			$( "#savefunction_output" ).modal(
				"show"
			);
		},
		project_import_data_change: function( new_project_data_json ) {
			try {
				import_project_data(
					JSON.parse(
						new_project_data_json
					)
				);
				app.import_paste_error = false;
			} catch ( e ) {
				app.import_paste_error = "Error! Invalid JSON."
				console.log( e );
			}
		},
		show_rename_project_modal: function() {
			$( "#project_name_rename_output" ).modal(
				"show"
			);
		},
		download_project_data: function() {
			download_file(
				get_project_json(),
				get_safe_name( app.project_name ) + ".json"
			);
		},
		export_project_data: function() {
			Vue.set( app, "project_data_json", get_project_json() );
			$( "#exportproject_output" ).modal(
				"show"
			);
		},
		import_project_data: function() {
			// Reset data
			app.import_paste_error = false;
			app.project_data_json = "";
			
			$( "#importproject_output" ).modal(
				"show"
			);
		},
		fullscreen_lambda_editor: function() {
			$( "#lambda_editor_popup" ).modal(
				"show"
			);
		},
		lambda_libraries_change: function( val ) {
			if( app.unformatted_libraries !== val ) {
				app.unformatted_libraries = val;
			}
		},
		lambda_code_change: function( val ) {
			if ( app.lambda_code !== val ) {
				app.lambda_code = val;
			}
		},
		conditional_data_expression_change: function( val ) {
			app.state_transition_conditional_data.expression = val;
		},
		sfn_input_data_change: function( val ) {
			if ( app.scheduled_trigger_data.unformatted_input_data !== val ) {
				app.scheduled_trigger_data.unformatted_input_data = val;
				
				// Try to parse as JSON
				try {
					app.scheduled_trigger_data.input_dict = JSON.parse(
						app.scheduled_trigger_data.unformatted_input_data
					);
				} catch ( e ) {
					app.scheduled_trigger_data.input_dict = app.scheduled_trigger_data.unformatted_input_data;
				}
				
				// Todo try to parse as Interger/Float/etc
			}
		},
		project_export_data_change: function( val ) {
			// Stub
		},
		run_tmp_lambda: function() {
			// Clear previous result
			app.lambda_exec_result = false;
			app.lambda_build_time = 0;
			
			// Time build
			var start_time = Date.now();
			
			$( "#runtmplambda_output" ).modal(
				"show"
			);
			
			run_tmp_lambda(
				app.lambda_language,
				app.lambda_code,
				app.lambda_libraries,
				app.lambda_memory,
				app.lambda_max_execution_time
			).then(function( results ) {
				console.log( "Run tmp lambda: " );
				console.log( results );
				var delta = Date.now() - start_time;
				app.lambda_build_time = ( delta / 1000 );
				app.lambda_exec_result = results.result;
			});
		},
		add_lambda: function() {
			var lambda_data = get_lambda_data();
			app.workflow_states.push( lambda_data );
		},
		navigate_page: function( page_id ) {
			app.page = page_id;
		},
		create_new_state_transition: function() {
			var default_state_transition_conditional_data = {
				"name": "then",
				// "then", "if", "else", "exception"
				"type": "then",
				"expression": "",
				"node": app.selected_node,
				"next": false,
			}
			
			var potential_next_pages = app.workflow_states.filter(function( workflow_state ) {
				return ( workflow_state.id !== app.selected_node );
			});
			
			if( potential_next_pages.length > 0 ) {
				default_state_transition_conditional_data.next = potential_next_pages[0].id;
			}
			
			Vue.set( app, "state_transition_conditional_data", default_state_transition_conditional_data );
			
			app.navigate_page( "add-state-transition" );
		},
		add_state_transition: function() {
			app.workflow_relationships.push({
				"id": get_random_node_id(),
				"name": app.state_transition_conditional_data.name,
				"type": app.state_transition_conditional_data.type,
				"expression": app.state_transition_conditional_data.expression,
				"node": app.selected_node,
				"next": app.state_transition_conditional_data.next,
			});
			app.navigate_page("welcome");
		},
		delete_state_transition: function() {
			app.workflow_relationships = app.workflow_relationships.filter(function( workflow_relationship ) {
				return workflow_relationship.id !== app.selected_transition;
			});
			app.navigate_page("welcome");
		},
		delete_node: function() {
			app.workflow_states = app.workflow_states.filter(function( workflow_state ) {
				return workflow_state.id !== app.selected_node;
			});
			app.workflow_relationships = app.workflow_relationships.filter(function( workflow_relationship ) {
				if( workflow_relationship[ "node" ] == app.selected_node ) {
					return false;
				}
				if( workflow_relationship[ "next" ] == app.selected_node ) {
					return false;
				}
				return true;
			});
			app.navigate_page("welcome");
		},
		update_node_data: function( node_id, new_node_data ) {
			app.workflow_states = app.workflow_states.map(function( workflow_state ) {
				if( workflow_state.id == node_id ) {
					return new_node_data;
				}
				return workflow_state;
			});
		},
		update_lambda: function() {
			var updated_lambda_data = {
				"id": app.selected_node,
				"name": app.lambda_name,
				"language": app.lambda_language,
				"libraries": app.lambda_libraries,
				"code": app.lambda_code,
				"memory": app.lambda_memory,
				"max_execution_time": app.lambda_max_execution_time,
				"type": "lambda",
			}
			
			app.update_node_data(
				app.selected_node,
				updated_lambda_data
			);
		},
		update_sqs_queue: function() {
			var updated_sqs_queue_data = {
				"id": app.selected_node,
				"name": app.sqs_trigger_data.queue_name,
				"type": "sqs_queue",
				"queue_name": app.sqs_trigger_data.queue_name,
				"content_based_deduplication": app.sqs_trigger_data.content_based_deduplication,
				"batch_size": app.sqs_trigger_data.batch_size,
				"sqs_job_template": app.sqs_trigger_data.sqs_job_template
			};
			
			app.update_node_data(
				app.selected_node,
				updated_sqs_queue_data
			);
		},
		update_schedule_trigger: function() {
			var updated_schedule_trigger = {
				"id": app.selected_node,
	            "name": app.scheduled_trigger_data.name,
	            "type": "schedule_trigger",
				"schedule_expression": app.scheduled_trigger_data.schedule_expression,
				"description": app.scheduled_trigger_data.description,
				"unformatted_input_data": app.scheduled_trigger_data.unformatted_input_data,
				"input_dict": app.scheduled_trigger_data.input_dict,
			};
			
			app.update_node_data(
				app.selected_node,
				updated_schedule_trigger
			);
		},
	}
});

// Auto-update data from Refinery ATC server
var atc_auto_updater = setInterval(function() {
	app.update_refinery_atc_data();
}, ( 1000 * 5 ));

build_dot_graph();

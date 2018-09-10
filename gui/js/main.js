var API_SERVER = location.origin.toString() + ":7777";
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

function updateGraph() {
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
    
    updateOutput();
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
}

function updateOutput() {
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
    return;
  }
  
	var svg = parser.parseFromString(result, "image/svg+xml").documentElement;
	svg.id = "svg_output";
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

/*
const VueAceEditor = {
    //  simplified model handling using `value` prop and `input` event for $emit
    props:['value','id','options'],

    //  add dynmic class and id (if not set) based on component tag
    template:`
        <div :id="id ? id: $options._componentTag +'-'+ _uid"
             :class="$options._componentTag">
            <slot></slot>
        </div>
    `,

    watch:{
        value() {
            //  two way binding – emit changes to parent
            this.$emit('input', this.value);
            
            //  update value on external model changes
            if(this.oldValue !== this.value){
                this.editor.setValue(this.value, 1);
            }
        }
    },
   
    mounted(){
        //  editor
        this.editor = window.ace.edit(this.$el.id);
        
        //  deprecation fix
        this.editor.$blockScrolling = Infinity;

        //  ignore doctype warnings
        const session = this.editor.getSession();
        session.on("changeAnnotation", () => {
            const a = session.getAnnotations();
            const b = a.slice(0).filter( (item) => item.text.indexOf('DOC') == -1 );
            if(a.length > b.length) session.setAnnotations(b);
        });

        //  editor options
        //  https://github.com/ajaxorg/ace/wiki/Configuring-Ace
        this.options = this.options || {};
        
        //  opinionated option defaults
        this.options.maxLines = this.options.maxLines || Infinity;
        this.options.printMargin = this.options.printMargin || false;
        this.options.highlightActiveLine = this.options.highlightActiveLine || false;

        //  hide cursor
        if(this.options.cursor === 'none' || this.options.cursor === false){
            this.editor.renderer.$cursorLayer.element.style.display = 'none';
            delete this.options.cursor;
        }

        //  add missing mode and theme paths
        if(this.options.mode && this.options.mode.indexOf('ace/mode/')===-1) {
            this.options.mode = `ace/mode/${this.options.mode}`;
        }
        if(this.options.theme && this.options.theme.indexOf('ace/theme/')===-1) {
            this.options.theme = `ace/theme/${this.options.theme}`;
        }
        this.editor.setOptions(this.options);
        
        
        //  set model value
        //  if no model value found – use slot content
        if(!this.value || this.value === ''){
            this.$emit('input', this.editor.getValue());
        } else {
            this.editor.setValue(this.value, -1);
        }
        
        //  editor value changes
        this.editor.on('change', () => {
            //  oldValue set to prevent internal updates
             this.value = this.oldValue = this.editor.getValue();
        });
        

    },
    methods:{ editor(){ return this.editor } }
};

*/

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
	return_data[ "code" ] = app.codecontent;
	return_data[ "memory" ] = app.lambda_memory;
	return_data[ "libraries" ] = app.code_imports;
	return return_data
}

function get_lambda_data_by_id( node_id ) {
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

function build_dot_graph() {
	var dot_contents = "digraph \"renderedworkflow\"{\n";
	
	app.workflow_states.map(function( workflow_state ) {
		var node_color = "ededed";
		var node_shape = "rectangle";
		
		if( workflow_state["id"] == app.selected_node ) {
			node_color = "fffa00";
		} else if ( workflow_state["id"] == "start_node" || workflow_state["id"] == "end_node" ) {
			// Start or End special node
			node_color = "ff7f00";
		}
		
		if( workflow_state[ "id" ] == "start_node" ) {
			node_shape = "circle";
		} else if ( workflow_state[ "id" ] == "end_node" ) {
			node_shape = "octagon";
		}
		
		dot_contents += "\t" + workflow_state["id"] + " [href=\"javascript:select_node('" + workflow_state["id"] + "')\", label=\"" + workflow_state["name"] + "\", fillcolor=\"#" + node_color + "\", style=\"filled\", shape=\"" + node_shape + "\"];\n";
	});
	
	app.workflow_relationships.map(function( workflow_relationship ) {
		dot_contents += "\t" + workflow_relationship["node"] + " -> " + workflow_relationship["next"];
		
		// "next" text next to transition
		dot_contents += " [penwidth=2, label=<<table cellpadding=\"10\" border=\"0\" cellborder=\"0\"><tr><td>next</td></tr></table>> href=\"javascript:select_transition('" + workflow_relationship[ "id" ] + "')\" ";
		
		//dot_contents += " [penwidth=2, href=\"javascript:select_transition('" + workflow_relationship[ "id" ] + "')\" ";
		
		if( workflow_relationship.id == app.selected_transition ) {
			dot_contents += "color=\"#ff0000\"";
		} else {
			dot_contents += "color=\"#000000\"";
		}
		
		dot_contents += "]\n"
	});
	
	dot_contents += "}";
	app.graphiz_content = dot_contents;
	
	console.log( dot_contents );
	updateGraph();
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
	if( app.selected_node == node_id && app.page == "modify-lambda" ) {
		app.selected_node = false;
	} else {
		app.selected_node = node_id;
	}
	
	// Can't have both selected
	if( app.selected_transition ) {
		app.selected_transition = false;
	}
	
	if( app.selected_node == "start_node" || app.selected_node == "end_node" ) {
		app.navigate_page("add-state-transition");
	} else if ( app.selected_node ) {
		//app.navigate_page("add-state-transition");
		// Set up temp variables
		reset_current_lambda_state_to_defaults();
		var selected_node_data = get_lambda_data_by_id( node_id );
		app.lambda_name = selected_node_data.name;
		app.lambda_language = selected_node_data.language;
		app.unformatted_code_imports = selected_node_data.libraries.join( "\n" );
		app.codecontent = selected_node_data.code;
		app.lambda_memory = selected_node_data.memory;
		app.navigate_page("modify-lambda");
	} else {
		app.navigate_page("welcome");
	}
	
	
	build_dot_graph();
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
		app.navigate_page("modify-state-transition");
	} else {
		app.navigate_page("welcome");
	}
	
	build_dot_graph();
}

function reset_current_lambda_state_to_defaults() {
	app.lambda_name = "";
	app.lambda_language = "python2.7";
	app.code_imports = [];
	app.unformatted_code_imports = "";
	app.codecontent = `
def main( lambda_input, context ):
	"""
	SQS message body: lambda_input[ "Records" ][0][ "body" ]
	"""
    return False
`;
}

function deploy_step_function( sfn_name, workflow_states, workflow_relationships ) {
	return api_request(
		"POST",
		"api/v1/aws/deploy_step_function",
		{
			"workflow_states": workflow_states,
			"workflow_relationships": workflow_relationships,
			"sfn_name": sfn_name,
		}
	);
}

function deploy_lambda( name, language, code, libraries, memory ) {
	return api_request(
		"POST",
		"api/v1/aws/deploy_lambda",
		{
			"name": name,
			"language": language,
			"code": code,
			"libraries": libraries,
			"memory": memory,
			"execution_time": 300
		}
	);
}

function run_tmp_lambda( language, code, libraries, memory ) {
	return api_request(
		"POST",
		"api/v1/aws/run_tmp_lambda",
		{
			"language": language,
			"code": code,
			"libraries": libraries,
			"memory": memory,
			"execution_time": 300
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

function create_lambda_input_sqs_queue( queue_name, content_based_deduplication, batch_size, lambda_arn ) {
	return api_request(
		"POST",
		"api/v1/aws/create_sqs_trigger",
		{
			"queue_name": queue_name,
			"content_based_deduplication": content_based_deduplication,
			"batch_size": batch_size,
			"lambda_arn": lambda_arn
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

ace.config.set( "basePath", "./js/" );
Vue.component('Editor', {
  template: '<div :id="editorId" style="width: 100%; height: 100%;"></div>',
  props: ['editorId', 'content', 'lang', 'theme'],
  data () {
    return {
      editor: Object,
      beforeContent: ''
    }
  },
  watch: {
    'content' (value) {
    	if (this.beforeContent !== value) {
      	this.editor.setValue(value, 1)
      }
    }
  },
  mounted () {
  	const lang = this.lang || 'python'
    const theme = this.theme || 'monokai'
  
	this.editor = window.ace.edit(this.editorId)
    this.editor.setValue(this.content, 1)
    
    this.editor.getSession().setMode(`ace/mode/${lang}`)
    this.editor.setTheme(`ace/theme/${theme}`)

    this.editor.on('change', () => {
    	this.beforeContent = this.editor.getValue()
      this.$emit('change-content', this.editor.getValue())
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
		workflow_states: [
		    {
		        "id": "start_node",
		        "name": "Start",
		        "language": "",
		        "code": "",
		        "libraries": [],
		        "memory": 0
		    },
		    {
		        "id": "end_node",
		        "name": "End",
		        "language": "",
		        "code": "",
		        "libraries": [],
		        "memory": 0
		    },
		    {
		        "id": "nac6cfe6a9d4448b399139a783a57f70e",
		        "name": "Step One",
		        "language": "python2.7",
		        "libraries": [],
		        "code": "\ndef main( lambda_input, context ):\n    print( \"pew\" )\n    return \"example\"\n",
		        "memory": 128
		    },
		    {
		        "id": "n8769324f65b04a23b63a9b0315e18884",
		        "name": "Step Two",
		        "language": "python2.7",
		        "libraries": [],
		        "code": "\ndef main( lambda_input, context ):\n    print( \"wat\" )\n    return str(lambda_input).upper()\n",
		        "memory": 128
		    }
		],
		workflow_relationships: [
		    {
		        "id": "n6637cf40d02244ff8a57989d0b555eea",
		        "node": "start_node",
		        "next": "nac6cfe6a9d4448b399139a783a57f70e"
		    },
		    {
		        "id": "n6a4b759e27554818bc59d713841597ac",
		        "node": "nac6cfe6a9d4448b399139a783a57f70e",
		        "next": "n8769324f65b04a23b63a9b0315e18884"
		    },
		    {
		        "id": "n85120fd907ec4105a9758bf46313141f",
		        "node": "n8769324f65b04a23b63a9b0315e18884",
		        "next": "end_node"
		    }
		],
		next_state_transition_selected: false,
		graphiz_content: "",
		// Project name
		project_name: "Example Project",
		// Currently selected lambda name
		lambda_name: "",
		// Currently selected lambda language
		lambda_language: "python2.7",
		// Currently selected lambda imports
		unformatted_code_imports: "",
		code_imports: [],
		// Currently selected lambda code
        codecontent: "",
        // Currently selected lambda max memory
        lambda_memory: 128,
        // The result of a lambda execution
        lambda_exec_result: false,
        // Lambda build timer
        lambda_build_time: 0,
        // Whether or not the step function deploy is loading
        step_function_deploy_loading: true,
        // Timer for building step function
        step_function_build_time: 0,
        // AWS link for built step function
        step_function_execution_link: false,
        // Which trigger type is being selected
        selected_trigger_type: "none",
    	// Target data for when a schedule-based trigger is created
        scheduled_trigger_data: {
        	"name": "Scheduled_Trigger_Example",
        	"schedule_expression": "rate(1 minute)",
        	"description": "Example scheduled rule description.",
        	"target_arn": "",
        	"target_id": "",
        	"target_type": "lambda",
        	"unformatted_input_data": "{}",
        	"input_dict": {},
        },
        // Target data for when an SQS-based trigger is created
        sqs_trigger_data: {
			"queue_name": "Example Queue",
			"content_based_deduplication": true,
			"batch_size": 1,
			"lambda_arn": "",
        },
        // Queue link
        sqs_queue_link: false,
        // Trigger link
        cloudwatch_event_link: false,
        // Status text for when deploying Step Function
        step_function_deploy_status_text: "Loading...",
        // Whether the lambda deploy is loading
        lambda_deploy_loading: true,
        // Deployed Lambda link
        lambda_deployed_link: "",
        // Status text while deploying lambda
        lambda_deploy_status_text: "Loading",
        
        codeoptions: {
            mode: "python",
            theme: "monokai",
            fontSize: 12,
            fontFamily: "monospace",
            highlightActiveLine: false,
            highlightGutterLine: false
        },
	},
	computed: {
		selected_node_data: function() {
			return get_lambda_data_by_id( app.selected_node );
		},
		selected_transition_data: function() {
			return get_state_transition_by_id( app.selected_transition );
		},
		aws_step_function_data: function() {
			return false
		}
	},
	methods: {
		fullscreen_lambda_editor: function() {
			$( "#lambda_editor_popup" ).modal(
				"show"
			);
		},
		codecontent_change: function( val ) {
			if ( app.codecontent !== val ) {
				app.codecontent = val;
			}
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
		code_imports_change: function ( val ) {
			if( app.unformatted_code_imports !== val ) {
				app.unformatted_code_imports = val.trim();
				if( app.unformatted_code_imports == "" ) {
					app.code_imports = [];
				} else {
					app.code_imports = app.unformatted_code_imports.split( "\n" );
				}
			}
		},
		open_step_function_execution_page: function() {
			window.open(
				app.step_function_execution_link
			);
		},
		open_cloudwatch_trigger_page: function() {
			window.open(
				app.cloudwatch_event_link
			);
		},
		select_trigger: function( target_type ) {
			// Reset data
	        var scheduled_trigger_data = {
	        	"name": app.lambda_name + " Trigger",
	        	"schedule_expression": "rate(1 minute)",
	        	"description": "Example scheduled rule description.",
	        	"target_arn": "",
	        	"target_id": "",
	        	"target_type": target_type,
	        	"input_dict": {},
	        	"unformatted_input_data": "{}",
	        }
	        Vue.set( app, "scheduled_trigger_data", scheduled_trigger_data );
	        
	        var sqs_trigger_data = {
				"queue_name": app.lambda_name + " Queue",
				"content_based_deduplication": true,
				"batch_size": 1,
				"lambda_arn": "",
	        }
	        Vue.set( app, "sqs_trigger_data", sqs_trigger_data );
	        
	        app.sqs_queue_link = false;
	        
	        app.selected_trigger_type = "none";
	        
			$( "#trigger_selection_modal" ).modal(
				"show"
			);
		},
		select_trigger_continue_action: function() {
			if( app.scheduled_trigger_data.target_type == "sfn" ) {
				app.deploy_step_function();
			} else if ( app.scheduled_trigger_data.target_type == "lambda" ) {
				app.deploy_lambda();
			}
		},
		deploy_step_function: function() {
			// Clear previous result
			app.step_function_deploy_loading = true;
			app.step_function_build_time = 0;
			app.step_function_execution_link = false;
			app.step_function_deploy_status_text = "Building and executing the Step Function, this may take a bit...";
			app.cloudwatch_event_link = false;
			
			$( "#runstepfunction_output" ).modal(
				"show"
			);
			
			// Time build
			var start_time = Date.now();
			
			deploy_step_function(
				app.project_name,
				app.workflow_states,
				app.workflow_relationships,
			).then(function( results ){
				var delta = Date.now() - start_time;
				app.step_function_build_time = ( delta / 1000 );
				app.step_function_execution_link = results[ "result" ][ "url" ];
				app.scheduled_trigger_data.target_arn = results[ "result" ][ "sfn_arn" ];
				app.scheduled_trigger_data.target_id = results[ "result" ][ "sfn_name" ];
				return
			}).then(function(){
				if( app.selected_trigger_type == "scheduled" ) {
					console.log( "Creating schedule-based trigger..." );
					app.step_function_deploy_status_text = "Creating the schedule-based trigger specified...";
					return create_schedule_trigger(
						app.scheduled_trigger_data.name,
						app.scheduled_trigger_data.schedule_expression,
						app.scheduled_trigger_data.description,
						"sfn",
						app.scheduled_trigger_data.target_id,
						app.scheduled_trigger_data.target_arn,
						app.scheduled_trigger_data.input_dict,
					).then(function( trigger_results ) {
						app.cloudwatch_event_link = trigger_results[ "result" ][ "url" ];
						return Promise.resolve();
					});
				} else {
					console.log( "No trigger set, just continueing..." );
					return Promise.resolve();
				}
			}).then(function( results ) {
				app.step_function_deploy_loading = false;
			});
		},
		deploy_lambda: function() {
			// Clear previous result
			app.lambda_exec_result = false;
			app.lambda_build_time = 0;
			app.lambda_deploy_loading = true;
			app.lambda_deployed_link = "";
			app.cloudwatch_event_link = false;
			
			$( "#deploylambda_output" ).modal(
				"show"
			);
			
			// Time build
			var start_time = Date.now();
			
			// Status text
			app.lambda_deploy_status_text = "Deploying Lambda...";
			
			deploy_lambda(
				app.lambda_name,
				app.lambda_language,
				app.codecontent,
				app.code_imports,
				app.lambda_memory
			).then(function( results ) {
				console.log( "Deployed lambda: " );
				console.log( results );
				var delta = Date.now() - start_time;
				app.lambda_build_time = ( delta / 1000 );
				app.lambda_deployed_link = results[ "url" ];
				app.scheduled_trigger_data.target_arn = results[ "arn" ];
				app.scheduled_trigger_data.target_id = results[ "name" ];
			}).then(function() {
				if( app.selected_trigger_type == "scheduled" ) {
					console.log( "Creating schedule-based trigger..." );
					app.lambda_deploy_status_text = "Creating the schedule-based trigger specified...";
					return create_schedule_trigger(
						app.scheduled_trigger_data.name,
						app.scheduled_trigger_data.schedule_expression,
						app.scheduled_trigger_data.description,
						"lambda",
						app.scheduled_trigger_data.target_id,
						app.scheduled_trigger_data.target_arn,
						app.scheduled_trigger_data.input_dict,
					).then(function( trigger_results ) {
						app.cloudwatch_event_link = trigger_results[ "result" ][ "url" ];
						return Promise.resolve();
					});
				} else if( app.selected_trigger_type == "sqs-queue" ) {
					return create_lambda_input_sqs_queue(
						app.sqs_trigger_data.queue_name,
						app.sqs_trigger_data.content_based_deduplication,
						app.sqs_trigger_data.batch_size,
						app.scheduled_trigger_data.target_arn
					).then(function( results ) {
						console.log( "SQS queue creation results: " );
						console.log( results );
						
						app.sqs_queue_link = results[ "queue_url" ];
						
						return Promise.resolve();
					});
				} else {
					console.log( "No trigger set, just continuing..." );
					return Promise.resolve();
				}
			}).then(function() {
				app.lambda_deploy_loading = false;
			});
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
				app.codecontent,
				app.code_imports,
				app.lambda_memory
			).then(function( results ) {
				console.log( "Run tmp lambda: " );
				console.log( results );
				var delta = Date.now() - start_time;
				app.lambda_build_time = ( delta / 1000 );
				app.lambda_exec_result = results.result;
			});
		},
		open_sqs_queue_page: function() {
			window.open(
				app.sqs_queue_link
			);
		},
		open_deployed_lambda_page: function() {
			window.open(
				app.lambda_deployed_link
			);
		},
		add_lambda: function() {
			var lambda_data = get_lambda_data();
			app.workflow_states.push( lambda_data );
			build_dot_graph();
		},
		navigate_page: function( page_id ) {
			app.page = page_id;
			if( app.page == "add-lambda" ) {
				reset_current_lambda_state_to_defaults();
			}
		},
		add_state_transition: function() {
			app.workflow_relationships.push({
				"id": get_random_node_id(),
				"node": app.selected_node,
				"next": app.next_state_transition_selected,
			});
			build_dot_graph();
			app.navigate_page("welcome");
		},
		delete_state_transition: function() {
			app.workflow_relationships = app.workflow_relationships.filter(function( workflow_relationship ) {
				return workflow_relationship.id !== app.selected_transition;
			});
			build_dot_graph();
			app.navigate_page("welcome");
		},
		delete_lambda: function() {
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
			build_dot_graph();
			app.navigate_page("welcome");
		},
		update_lambda: function() {
			var updated_lambda_data = {
				"id": app.selected_node,
				"name": app.lambda_name,
				"language": app.lambda_language,
				"libraries": app.code_imports,
				"code": app.codecontent,
				"memory": app.lambda_memory
			}
			
			app.workflow_states = app.workflow_states.map(function( workflow_state ) {
				if( workflow_state.id == app.selected_node ) {
					return updated_lambda_data;
				}
				return workflow_state;
			});
			
			build_dot_graph();
		}
	}
});

build_dot_graph();
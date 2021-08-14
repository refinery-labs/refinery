const node810BaseCode = `
const { main } = require('./block_code.js');

backpack = {};
__input_data = "";

process.stdin.setEncoding("utf8");

process.stdin.on('readable', function() {
	var chunk;
	while (chunk = process.stdin.read()) {
		__input_data += chunk;
	}
});

process.stdin.on('end', function () {
	__rfn_init();
});

function __returnResult(programOutput) {
	console.log(
		"<REFINERY_OUTPUT_CUSTOM_RUNTIME_START_MARKER>" + JSON.stringify(
			programOutput
		) + "<REFINERY_OUTPUT_CUSTOM_RUNTIME_END_MARKER>"
	);
}

/**
 * Wraps a function with a promise. Returns a new function that can be called with await.
 */
function __promisify(fn) {
	return function promiseWrappedFunction() {
		return new Promise((resolve, reject) => {
			function wrapCallback(err, result) {
				// If error, reject the promise.
				if (err) {
					return reject(err);
				}
				// Call resolve to close the promise
				resolve(result);
			}

			// Concatenate to arguments list the wrapCallback function
			const argumentsList = [
				...(Array.prototype.slice.apply(arguments)),
				wrapCallback
			];

			// Call the wrapped function
			fn.apply(this, argumentsList);
		});
	}
}

async function __rfn_init() {
  try {
		if (process.stdout._handle) {
			process.stdout._handle.setBlocking(true);
		}

		// Inside of the try catch statement to ensure that any exceptions thrown here are logged.
		const inputData = JSON.parse( __input_data );
		const lambdaInput = inputData[ "lambda_input" ];
		backpack = inputData[ "backpack" ];

		const mainCallbackDefined = typeof mainCallback !== 'undefined';
		const mainDefined = typeof main !== 'undefined';

		if (!mainCallbackDefined && !mainDefined) {
			throw new Error('No main function was defined for block. You must specify a function named either \`main\` or \`mainCallback\` for a block to be valid and for it to run.');
		}

		if (mainCallbackDefined && mainDefined) {
			throw new Error('Both main and mainCallback were both defined, only one one entry point may be defined per block per block. Please delete or rename one of them.');
		}

		// Identify which function we will call as our entry point based on what was defined in the script.
		// If it's a callback, we wrap it with a promise so that we may await it.
		const mainEntrypoint = mainDefined ? main : __promisify(mainCallback);

		const output = await mainEntrypoint(lambdaInput);

		__returnResult({
      "output": output,
      "backpack": backpack,
    });

    backpack = {};
    flushProcessOutputsAndExit__refinery(0);
  } catch ( e ) {
    if( e.stack ) {
      e = e.stack.toString()
    } else {
      e = e.toString();
    }
    console.log(
      "<REFINERY_ERROR_OUTPUT_CUSTOM_RUNTIME_START_MARKER>" + JSON.stringify({
        "output": e,
        "backpack": backpack
      }) + "<REFINERY_ERROR_OUTPUT_CUSTOM_RUNTIME_END_MARKER>"
    );
    backpack = {};
    flushProcessOutputsAndExit__refinery(-1);
  }
}

function flushProcessOutputsAndExit__refinery(exitCode) {
  // Configure the streams to be blocking
  makeBlockingStream__refinery(process.stdout);
  makeBlockingStream__refinery(process.stderr);


  // Allow Node to cleanup any internals before the next process tick
  setImmediate(function callProcessExitWithCode() {
    process.exit(exitCode);
  });
}

function makeBlockingStream__refinery(stream) {
  if (!stream || !stream._handle || !stream._handle.setBlocking) {
    // Not able to set blocking so just bail out
    return;
  }

  stream._handle.setBlocking(true);
}
`;

const PYTHON_BASE_CODE = `
#!/bin/python
# This code hasn't been tested, and you'll have to fix it yourself. However, this does roughly what it needs to do.
# You probably need to add an "__init__.py" file to this folder in order to use the import syntax in Python.

import traceback
import json
import sys

def _init():
  raw_input_data = sys.stdin.read()
  input_data = json.loads( raw_input_data )
  lambda_input = input_data[ "lambda_input" ]
  backpack = input_data[ "backpack" ]

  try:
    # This call to main will need to import the code in "code_block.py"
    output = main( lambda_input, backpack )
    print( "<REFINERY_OUTPUT_CUSTOM_RUNTIME_START_MARKER>" + json.dumps({
      "backpack": backpack,
      "output": output,
    }) + "<REFINERY_OUTPUT_CUSTOM_RUNTIME_END_MARKER>" )
    backpack = {}
  except:
    print( "<REFINERY_ERROR_OUTPUT_CUSTOM_RUNTIME_START_MARKER>" + json.dumps({
      "backpack": backpack,
      "output": traceback.format_exc()
    }) + "<REFINERY_ERROR_OUTPUT_CUSTOM_RUNTIME_END_MARKER>" )
    backpack = {}
    exit(-1)
    
  exit(0)
_init()
`;

export const UNIMPLEMENTED_BASE_CODE_MESSAGE =
  '# Unimplemented Base Code. You will have to write a function that calls the code block in this folder manually.';

export const languageToBaseCodeLookup: Record<string, string> = {
  'nodejs8.10': node810BaseCode,
  'nodejs10.16.3': node810BaseCode,
  'nodejs10.20.1': node810BaseCode,
  'python2.7': PYTHON_BASE_CODE,
  'python3.6': PYTHON_BASE_CODE
};

const safeCompare = require('safe-compare');
const bodyParser = require('koa-bodyparser');
const validateJSON = require('jsonschema').validate;
const Router = require('koa-router');
const Koa = require('koa');

const goBuilder = require('./gobuilder');

const app = new Koa();
const router = new Router();
app.use(bodyParser());

// This is the latest timestamp
var lastBuildTimestamp = getUnixTimestamp();

// Max amount of time allowed to idle without being
// send a build before shutting down. If no max is set
// we do an hour by default.
const maxServerIdleMinutes = process.env.MAX_IDLE_TIME ? process.env.MAX_IDLE_TIME : 60;
console.log("Max server idle minutes:");
console.log(maxServerIdleMinutes);

// Every second, check if we've been idling past
// the max idle time. If we have then exit.
setInterval(function() {
	const currentTimestamp = getUnixTimestamp();
	const secondsSinceLastBuild = (currentTimestamp - lastBuildTimestamp);

	if(secondsSinceLastBuild >= ( maxServerIdleMinutes * 60 )) {
		console.log(`[Notice] No build has occurred in at least ${maxServerIdleMinutes} minute(s). Shutting down...`);
		process.exit();
	}
}, ( 1 * 1000 ));

// Intialize Go builds
goBuilder.initializeGoBuilds();

// If we don't have an AGENT_SECRET set, quit out.
if(!process.env.AGENT_SECRET) {
	console.error('No AGENT_SECRET defined, please set the environment variable to use this agent.');
	process.exit(-1);
}

// Stateful HTTP methods
const STATEFUL_HTTP_METHODS = [
	'POST',
	'PUT',
	'DELETE'
];

// The HTTP port the agent sits on
const AGENT_PORT = 2222;

// The header name used to authenticate API requests
const AGENT_SECRET_HEADER = 'X-Agent-Key';

// The secret for the agent
const AGENT_SECRET = process.env.AGENT_SECRET;

function getUnixTimestamp() {
	return Math.floor(Date.now() / 1000);
}

function requestMatchesJSONSchema(ctx, jsonSchema) {
	const validationResult = validateJSON(ctx.request.body, jsonSchema);
	return (validationResult.errors.length === 0);
}

/*
	Middleware to block all requests that are not properly
	authenticated via a shared secret.
*/
app.use(async (ctx, next) => {
	const sharedSecret = ctx.get(AGENT_SECRET_HEADER) ? ctx.get(AGENT_SECRET_HEADER) : '';

	// Use a constant-time check for the secret to prevent
	// timing attacks against the agent secret.
	if(!safeCompare(sharedSecret, AGENT_SECRET)) {
		ctx.throw(401, 'Invalid shared secret provided. Please provide the proper agent key to access this API.');
	}
	
	await next();
});

const goBuildSchema = {
	"type": "object",
	"properties": {
		"shared_files": {
			"type": "array"
		},
		"base_code": {
			"type": "string"
		},
		"libraries": {
			"type": "array"
		}
	},
	"required": [
		"shared_files",
		"base_code",
		"libraries"
	]
}
router.post('/api/v1/go/build', async (ctx, next) => {
	if(!requestMatchesJSONSchema(ctx, goBuildSchema)) {
		ctx.throw(401, 'Request body invalid, please use the correct format.');
	}

	// Update last build timestamp so the container doesn't exit
	lastBuildTimestamp = getUnixTimestamp();

	// Get the compiled Go binary, write errors if they occur
	try {
		const compiledGoBinary = await goBuilder.buildGoBinary(
			ctx.request.body.base_code,
			ctx.request.body.shared_files,
			ctx.request.body.libraries,
		);
		ctx.response.set('Content-Type', 'application/octet-stream');
		ctx.response.set('X-Compile-Status', 'SUCCESS');
		ctx.response.body = compiledGoBinary;
	} catch ( e ) {
		if( e instanceof goBuilder.GoGetError ) {
			ctx.response.set('Content-Type', 'text/plain');
			ctx.response.set('X-Compile-Status', 'GO_GET_ERROR');
		} else if ( e instanceof goBuilder.GoBuildError ) {
			ctx.response.set('Content-Type', 'text/plain');
			ctx.response.set('X-Compile-Status', 'GO_BUILD_ERROR');
		} else {
			ctx.response.set('Content-Type', 'text/plain');
			ctx.response.set('X-Compile-Status', 'UNKNOWN');
		}
		ctx.response.body = e.toString();
	}
});

app.use(router.routes()).use(router.allowedMethods());

console.log(`[STATUS] Refinery agent has started on 0.0.0.0:${AGENT_PORT}...`);
app.listen(AGENT_PORT);
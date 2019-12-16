const uuidv4 = require('uuid/v4');
const fs = require('fs').promises;
const fsOld = require('fs');
const { spawn } = require('child_process');

const goBaseBuildDir = '/tmp/gobuilds';
const goCacheDir = `${goBaseBuildDir}/cache`;

// Ensure we've created out base Go directory
function initializeGoBuilds() {
	const directoriesToCreate = [
		goBaseBuildDir,
		goCacheDir
	];

	directoriesToCreate.map(directoryToCreate => {
		if(!fsOld.existsSync(directoryToCreate)) {
			console.log(`[Initialization] Creating directory '${directoryToCreate}'...`);
			fsOld.mkdirSync(directoryToCreate);
		}
	});
}

// Custom exceptions for builds
class GoBaseError extends Error {
	constructor(message) {
		super(message);
		this.name = this.constructor.name;
		Error.captureStackTrace(this, this.constructor);
	}
}
class GoGetError extends GoBaseError {}
class GoBuildError extends GoBaseError {}

async function buildGoBinary(baseCode, sharedFiles, libraries) {
	const buildID = uuidv4();
	const buildBasePath = `${goBaseBuildDir}/${buildID}`;

	console.log(`Creating base directory ${buildBasePath}...`);
	await fs.mkdir(buildBasePath);

	try {
		const result = await _buildGoBinary(
			buildID,
			buildBasePath,
			baseCode,
			sharedFiles,
			libraries
		)
		removeBuildDirectory(buildBasePath);
		return result;
	} catch( e ) {
		removeBuildDirectory(buildBasePath);
		throw e;
	}
}

async function _buildGoBinary(buildID, buildBasePath, baseCode, sharedFiles, libraries) {
	const goBuildEnvVars = {
		'GOCACHE': goCacheDir,
		'GOPATH': goBaseBuildDir
	};

	console.log('Writing base code...');
	await writeTextFile(
		`${buildBasePath}/main.go`,
		baseCode
	);
	
	console.log(`Starting build...`);

	console.log('Pulling the following packages:');
	libraries.map(library => console.log(library));

	// Pull all of the Go packages
	console.log(`Build base path ${buildBasePath}...`);

	// Skip if there are no libraries to get.
	if(libraries.length > 0) {
		console.log('Running "go get"..."');
		const goGetStartTime = +new Date();
		try {
			const packageOutput = await executeBinary(
				'go',
				[
					'get'
				].concat( libraries ),
				buildBasePath,
				goBuildEnvVars
			);
		} catch ( e ) {
			console.log('"go get" exception: ' );
			console.log(e);
			throw new GoGetError(e);
		}

		const goGetEndTime = +new Date();
		console.log(`"go get" took ${(goGetEndTime-goGetStartTime)/1000} second(s).`);
	}

	// Build the Go binary
	console.log('Running "go build"...');
	const goBuildStartTime = +new Date();
	try {
		const buildOutput = await executeBinary(
			'go',
			[
				'build',
				'-o',
				'lambda'
			],
			buildBasePath,
			goBuildEnvVars
		);
	} catch ( e ) {
		console.log('"go build" exception: ' );
		console.log(e);
		throw new GoBuildError(e);
	}
	const goBuildEndTime = +new Date();
	console.log(`"go build" took ${(goBuildEndTime-goBuildStartTime)/1000} second(s).`);

	// Read the compiled binary from disk
	return getFile(`${buildBasePath}/lambda`);
}

async function removeBuildDirectory(buildBasePath) {
	// Delete the build directory entirely
	console.log('Cleaning up build directory...');

	// Don't await because there's no reason to wait for it to finish
	// before returning the binary
	executeBinary(
		'rm',
		[
			'-rf',
			buildBasePath
		],
		buildBasePath
	);
}

async function getFile(filePath) {
	return fs.readFile(filePath);
}

async function writeTextFile(filePath, fileBody) {
	const bodyBuffer = new Uint8Array(Buffer.from(fileBody, 'utf8'));
	await fs.writeFile(filePath, bodyBuffer);
}

function executeBinary( binary_location, binary_arguments, cwd, env ) {
	return new Promise(function(resolve, reject) {
		let stdout = "";
		let stderr = "";

		// Base case for env if not set.
		if(!env) {
			env = {};
		}

		const process_env = {
			...process.env,
			...env
		}

		const child = spawn(
			binary_location,
			binary_arguments,
			{
				"cwd": cwd,
				"env": process_env
			}
		);

		child.stdout.setEncoding('utf8');
		child.stdout.on('data', (chunk) => {
			stdout += chunk;
		});

		child.stderr.setEncoding('utf8');
		child.stderr.on('data', (chunk) => {
			stderr += chunk;
		});

		child.on('close', (code) => {
			if(stderr != "") {
				reject(stderr);
				return
			}
			resolve(stdout);
		});
	});
}

exports.buildGoBinary = buildGoBinary;
exports.initializeGoBuilds = initializeGoBuilds;
exports.GoGetError = GoGetError;
exports.GoBuildError = GoBuildError;
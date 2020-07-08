const util = require('util');
const exec = util.promisify(require('child_process').exec);
const readFile = util.promisify(require('fs').readFile);

async function removeAccount(email) {
	console.log(`Removing email: ${email}`);
  const { stdout, stderr } = await exec(`sls invoke local -f deleteAccount -l --log-type Tail --data '{"email": "${email}"}'`);
  console.log('stdout:', stdout);
  console.error('stderr:', stderr);

	if (!stdout.includes('successfully deleted account')) {
		throw `Unable to remove email ${email}`;
	}
}

async function removeAllAccounts() {
	const contents = await readFile('accounts_to_remove.txt', 'utf8');
	await contents.split('\n').reduce(async (emails, email) => {
		console.log(emails);
		const awaitedEmails = await emails;
		if (email.length > 0) {
			await removeAccount(email);
		}
		return [
			...awaitedEmails,
			email
		];
	}, Promise.resolve([]));
}

removeAllAccounts().then(() => console.log('done'));

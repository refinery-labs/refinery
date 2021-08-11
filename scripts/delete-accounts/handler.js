const dbc = require('./deathbycaptcha');
const download = require('image-downloader');
const axios = require('axios');
const puppeteer = require('puppeteer-core');
const chrome = require('chrome-aws-lambda');
const crypto = require('crypto');

const awsLandingURL = 'https://signin.aws.amazon.com/signin?redirect_uri=https%3A%2F%2Fconsole.aws.amazon.com%2Fbilling%2Fhome%3Fstate%3DhashArgs%2523%252Faccount%26isauthcode%3Dtrue&client_id=arn%3Aaws%3Aiam%3A%3A934814114565%3Auser%2Fportal-aws-auth&forceMobileApp=0';

const MAX_ATTEMPT_RETRY = 5;
const PASSWORD_RESET_SUBJECT = 'Amazon Web Services Password Assistance';
const MAILGUN_API_KEY = process.env['MAILGUN_API_KEY'];
const DBC_USERNAME = process.env['DBC_USERNAME'];
const DBC_PASSWORD = process.env['DBC_PASSWORD'];
const PASSWORD_REQUIREMENTS = '1!aA';

async function getSavedEmails(email) {
  const items = await axios.get(
    'https://api.mailgun.net/v3/mail.refineryusercontent.com/events',
    {
      headers: {
        'Accept': 'message/rfc2822'
      },
      params: {
        'recipient': email
      },
      auth: {
        username: 'api',
        password: MAILGUN_API_KEY
      }
    })
    .then(response => {
      return response.data.items;
    })
    .catch(err => {
      throw err;
    });

  const urls = items.filter(
    item => item.message.headers.subject === PASSWORD_RESET_SUBJECT
  ).map(
    item => item.storage.url
  );
  if (urls.length === 0) {
    return '';
  }
  return getResetLinkForMessage(urls[0])
}

async function getResetLinkForMessage(url) {
  return axios.get(url, {
      auth: {
        username: 'api',
        password: MAILGUN_API_KEY
      }
    })
    .then(response => {
      const toEmail = response.data.To;
      const body = response.data['body-html'].replace('=\r\n', '');

      const regex = /https:\/\/signin.aws.amazon.com\/resetpassword[^<]+/g
      const resetLinkMatches = body.match(regex);
      if (resetLinkMatches.length < 1) {
        return '';
      }
      return resetLinkMatches[resetLinkMatches.length - 1].replace('=3D', '');
    })
    .catch(err => {
      throw err;
    });
}

async function solveRateLimitingCaptcha(page) {
  const shouldSolveRateLimitCaptcha = await page.waitForSelector('#captcha_image', {
    visible: true, timeout: 4000
  }).then(() => {
    return true;
  }).catch((error) => {
    console.log('did not see rate limit captcha pop up');
    return false;
  });

  // determine if the rate limit captcha popped up
  if (shouldSolveRateLimitCaptcha) {
    console.log('rate limiting captcha is present, solving it');
    const imgUrl = await page.$eval('#captcha_image', el => el.src);
    const solution = await solveCaptcha(imgUrl);
    if (solution === undefined) {
      console.log('solution is undefined');
      process.exit();
    }

    await page.evaluate((solution) => {
      document.getElementById('captchaGuess').value = solution
    }, solution);
    await page.waitFor(1000);
    await page.click('#submit_captcha');
  }
}

async function saveImageToDisk(url, localPath) {
  const options = {
    url: url,
    dest: localPath
  }

  await download.image(options)
    .then(({filename, image}) => {
      console.log('Saved to', filename)
    })
    .catch((err) => console.error(err))
}

async function solveCaptchaWithClient(dbcClient, imageName) {
  // uploads and polls for decoded image
  return await new Promise((resolve, reject) => {
    dbcClient.decode({captcha: imageName}, (captcha, err) => {
      if (err !== undefined) {
        reject(err);
        return;
      }
      resolve(captcha['text']);
    });
  }).then((captcha) => {
    return captcha;
  }).catch((e) => {
    throw e;
  });
}

async function solveCaptcha(imgUrl) {
  const imageName = '/tmp/captcha.jpg';
  await saveImageToDisk(imgUrl, imageName);

  try {
    const dbcClient = new dbc.HttpClient(DBC_USERNAME, DBC_PASSWORD);
    return solveCaptchaWithClient(dbcClient, imageName);
  } catch (e) {
    console.log('unable to resolve captcha with http client, trying with socket client');
    const dbcClient = new dbc.SocketClient(DBC_USERNAME, DBC_PASSWORD);
    return solveCaptchaWithClient(dbcClient, imageName);
  }
}

function generatePassword() {
  return crypto.randomBytes(32).toString('hex') + PASSWORD_REQUIREMENTS;
}

async function solveForgotPasswordCaptcha(page) {
  console.log('solve forgot password page captcha');
  await page.waitForSelector('#password_recovery_captcha_image', {visible: true});
  await page.waitFor(1000);
  const imgUrl = await page.$eval('#password_recovery_captcha_image', el => el.src);
  const solution = await solveCaptcha(imgUrl);

  // set captcha guess
  await page.evaluate((solution) => {
    document.getElementById('password_recovery_captcha_guess').value = solution
  }, solution);
  await page.waitFor(1000);
}

async function initiatePasswordReset(page, email) {
  console.log('loading login page');
  await page.waitForSelector('#resolving_input');
  await page.evaluate((email) => {
    document.getElementById('resolving_input').value = email
  }, email);
  await page.click('#next_button');

  // if the rate limiting captcha pops up, solve it
  await solveRateLimitingCaptcha(page);

  console.log('waiting for forgot password page to load');
  await page.waitForSelector('#root_forgot_password_link', {visible: true});
  await page.click('#root_forgot_password_link');

  await solveForgotPasswordCaptcha(page);

  // confirm password reset captcha
  await page.click('#password_recovery_ok_button');
}

async function fetchPasswordResetURL(email) {
  console.log('asking mailgun for the reset link');

  // wait up to 5 more seconds if not found on the first try
  for (var i = 0; i < 5; i++) {
    let resetPasswordURL = await getSavedEmails(email);
    if (resetPasswordURL !== '') {
      return resetPasswordURL;
    }
    console.log('unable to get password reset URL, retrying...');
    await page.waitFor(1000);
  }

  // can't move forward at this point if we still haven't found the password reset url
  throw new Error('unable to get password reset url');
}

async function resetAccountPassword(page, tmpPassword) {
  console.log('reseting the password to:', tmpPassword);
  await page.waitForSelector('#new_password');
  await page.evaluate((password) => {
    document.getElementById('new_password').value = password
  }, tmpPassword);
  await page.evaluate((password) => {
    document.getElementById('confirm_password').value = password
  }, tmpPassword);

  console.log('throttle clicking submit button, because...');
  await page.waitFor(1000);
  await page.click('#reset_password_submit');

  console.log('waiting for success...');
  await page.waitForSelector('#success_link');
}

async function loginToAccount(page, email, tmpPassword) {
  console.log('loading email page');
  await page.waitForSelector('#resolving_input');
  await page.evaluate((email) => {
    document.getElementById('resolving_input').value = email
  }, email);
  await page.click('#next_button');

  // if the rate limiting captcha pops up, solve it
  await solveRateLimitingCaptcha(page);

  console.log('loading password page');
  await page.waitForSelector('#password');
  await page.waitFor(4000);
  await page.evaluate((password) => {
    document.getElementById('password').value = password
  }, tmpPassword);
  await page.waitFor(200);
  await page.click('#signin_button');
  console.log('sign in button clicked');
}

async function disableAccount(page) {
  console.log('wait for the account page to load');

  await page.goto('https://console.aws.amazon.com/billing/home?#/account');

  await page.waitFor(5000);

  // console.log('page contents:', await page.content());

  await page.waitForSelector('button[data-testid="aws-billing-account-form-button-close-account"]', {
    timeout: 60000
  });
  await page.$eval('.close-account-checkbox > input', el => el.checked = true);

  await page.$eval('button[data-testid="aws-billing-account-form-button-close-account"]', el => {
    el.disabled = false;
    el.click()
  });

  console.log('clicked button... waiting for selector again')

  await page.waitForSelector('button[data-testid="aws-billing-account-modal-button-close-account"]');
  await page.click('button[data-testid="aws-billing-account-modal-button-close-account"]');
}

async function resetPasswordDeleteAccount(page, email) {
  const tmpPassword = generatePassword();

  console.log('Email:', email);
  console.log('Password:', tmpPassword);

  await page.goto(awsLandingURL);

  await initiatePasswordReset(page, email);

  console.log('waiting for email to go to mailgun');
  await page.waitFor(10000);

  // mailgun api call to get password reset link
  const resetPasswordURL = await fetchPasswordResetURL(email);

  console.log('got reset url, going to that page now');
  await page.goto(resetPasswordURL);

  await resetAccountPassword(page, tmpPassword);

  console.log('going to the login page');
  await page.goto(awsLandingURL);

  await loginToAccount(page, email, tmpPassword);

  return true;
}

async function attemptPasswordReset(page, email) {
  let retryCount = 0;
  while (retryCount < MAX_ATTEMPT_RETRY) {
    try {
      console.log('trying to delete account');
      await resetPasswordDeleteAccount(page, email);
      break;
    } catch (e) {
      console.error('ERROR! deleting account ' + e.stack || e);
    }
    retryCount += 1;
  }
  return retryCount < MAX_ATTEMPT_RETRY;
}

async function deleteAccount(event, context, callback) {
  const email = event.email;

  if (!email) {
    throw new Error('Missing email for request');
  }

  try {
    const browser = await puppeteer.launch({
      args: chrome.args,
	    executablePath: await chrome.executablePath,
      headless: chrome.headless,
    });
    const page = await browser.newPage();

    const success = await attemptPasswordReset(page, email);

    console.log('password reset successful')

    await page.waitFor(500);

    await disableAccount(page);

    // TODO make sure network request goes through?
    await page.waitFor(4000);

    await browser.close();

    if (success) {
      console.log('DELETED ACCOUNT SUCCESS: ', email);
      const msg = 'successfully deleted account';
      return context.succeed(msg);
    } else {
      const msg = 'ERROR! unable to delete the account: ' + email + ' after retrying';
      console.error(msg);
      return context.fail(msg);
    }
  } catch (e) {
    console.error(e);
    return context.fail(e.stack || e);
  }
}

module.exports.deleteAccount = deleteAccount;

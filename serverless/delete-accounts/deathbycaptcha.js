/*

Death by Captcha HTTP and Socket API clients.

There are two types of Death by Captcha (DBC hereinafter) API: HTTP and
Socket ones.  Both offer the same functionalily, with the socket API
sporting faster responses and using way less connections.

To access the Socket API, use SocketClient class; for the HTTP API, use
HttpClient class.

Both SocketClient and HttpClient give you the following methods:

get_user((user) => {})
    Returns your DBC account details as a JSON with the following keys:

    "user": your account numeric ID; if login fails, it will be the only
        item with the value of 0;
    "rate": your CAPTCHA rate, i.e. how much you will be charged for one
        solved CAPTCHA in US cents;
    "balance": your DBC account balance in US cents;
    "is_banned": flag indicating whether your account is suspended or not.

get_balance((balance) => {})
    Returns your DBC account balance in US cents (null for invalid user).

get_captcha(cid, (captcha) => {})
    Returns an uploaded CAPTCHA details as a JSON with the following keys:

    "captcha": the CAPTCHA numeric ID; if no such CAPTCHAs found, it will
        be the only item with the value of 0;
    "text": the CAPTCHA text, if solved, otherwise None;
    "is_correct": flag indicating whether the CAPTCHA was solved correctly
        (DBC can detect that in rare cases).

    The only argument `cid` is the CAPTCHA numeric ID.

get_text(cid, (text) => {})
    Returns an uploaded CAPTCHA text (null if not solved).  The only argument
    `cid` is the CAPTCHA numeric ID.

report(cid, (success) => {})
    Reports an incorrectly solved CAPTCHA.  The only argument `cid` is the
    CAPTCHA numeric ID.  Returns true on success, false otherwise.

upload({captcha=null, extra={}}, (captcha) => {})
    Uploads a CAPTCHA.  The only argument `captcha` is the CAPTCHA image
    file name.  On successul upload you'll get the CAPTCHA details JSON
    (see get_captcha() method).

    NOTE: AT THIS POINT THE UPLOADED CAPTCHA IS NOT SOLVED YET!  You have
    to poll for its status periodically using get_captcha() or get_text()
    method until the CAPTCHA is solved and you get the text.

decode({captcha=null, timeout=null, extra={}}, (captcha) => {})
    A convenient method that uploads a CAPTCHA and polls for its status
    periodically, but no longer than `timeout` (defaults to 60 seconds).
    If solved, you'll get the CAPTCHA details JSON (see get_captcha()
    method for details).  See upload() method for details on `captcha`
    argument.

Visit http://www.deathbycaptcha.com/user/api for updates.

*/

const net = require('net');
const FormData = require('form-data');
const fs = require('fs');
const util = require('util')

// API version and unique software ID
const API_VERSION = 'DBC/NodeJS v4.6';

// Base HTTP API url
const HTTP_BASE_URL = 'api.dbcapi.me';

// Preferred HTTP API server's response content type, do not change...!!!
const HTTP_RESPONSE_TYPE = 'application/json';

const TERMINATOR = '\r\n';

// Default CAPTCHA timeout and decode() polling interval
const DEFAULT_TIMEOUT = 60;
const DEFAULT_TOKEN_TIMEOUT = 120;
const POLLS_INTERVAL = [1, 1, 2, 3, 2, 2, 3, 2, 2];
const DFLT_POLL_INTERVAL = 3;

function getRandomInt(min, max) {
  const a = Math.ceil(min);
  const b = Math.floor(max);
  return Math.floor(Math.random() * (b - a + 1)) + a;
};

function load_image(image) {
  const image_regex = RegExp('\.jpg$|\.png$|\.gif$|\.bmp$');
  const b64_regex = RegExp('^base64:');
  if (image_regex.test(image)) {
    return fs.readFileSync(image, {'encoding': 'base64'});
  } else if (b64_regex.test(image)) {
    return image.substring(7);
  } else {
    return image.toString('base64');
  }
};

class Client {

  // Death by Captcha API Client.

  constructor(username, password) {
    this.userpwd = {
      'username': username,
      'password': password
    };
  };

  get_balance(cb) {
    // Fetch user balance (in US cents).
    this.get_user((user) => {
      cb(user ? user['balance'] : null);
    });
  };

  get_text(cid, cb) {
    // Fetch a CAPTCHA text.
    this.get_captcha(cid, (captcha) => {
      cb(captcha ? captcha['text'] : null);
    });
  };

  decode({captcha=null, timeout=null, extra={}}, cb) {

    // Try to solve a CAPTCHA.

    // See Client.upload() for arguments details.

    // Uploads a CAPTCHA, polls for its status periodically with arbitrary
    // timeout (in seconds), returns CAPTCHA details if (correctly) solved.

    if (!timeout) {
      if (!captcha) {
        timeout = DEFAULT_TOKEN_TIMEOUT;
      } else {
        timeout = DEFAULT_TIMEOUT;
      }
    }
    const deadline = Date.now() + (0 < timeout ? timeout : DEFAULT_TIMEOUT) * 1000;
    this.upload({captcha: captcha, extra: extra}, (uploaded_captcha) => {
      if (uploaded_captcha) {
        const intvl_idx = 0;
        (function poll_interval(client, deadline, idx, captcha, cb) {
          if ((deadline > Date.now()) && (!captcha['text'])) {
            if (POLLS_INTERVAL.length > idx) {
              var intvl = POLLS_INTERVAL[idx] * 1000;
            } else {
              var intvl = DFLT_POLL_INTERVAL * 1000;
            }
            setTimeout(() => {
              client.get_captcha(captcha['captcha'], (uploaded_captcha) => {
                poll_interval(client, deadline, idx + 1, uploaded_captcha, cb)
              })
            }, intvl);
          } else if (captcha['text'] && captcha['is_correct']) {
            cb(captcha);
          } else cb(null);
        })(this, deadline, intvl_idx, uploaded_captcha, cb);
      } else {
        cb(null);
      };
    });
  };

};

class HttpClient extends Client {

  // Death by Captcha HTTP API client.

  _call({cmd, payload=null, headers={}, files=null}, cb) {

    var form = new FormData();

    var options = {
      protocol: 'http:',
      host: HTTP_BASE_URL,
      path: '/api/' + cmd
    };

    if (payload) {
      for (var entry in payload) {
        form.append(entry, payload[entry]);
      };
      if (files) {
        for (var file_key in files) {
          form.append(file_key, files[file_key]);
        };
      };
      options['headers'] = form.getHeaders();
    } else {
      options['method'] = 'GET';
      options['headers'] = headers;
    };

    options['headers']['Accept'] = HTTP_RESPONSE_TYPE;
    options['headers']['User-Agent'] = API_VERSION;

    const request = form.submit(options, (err, response) => {
      if (err) {
        throw new Error(err.message);
      } else {
        switch (response.statusCode) {
          case 200:
          case 303:
            var data = '';
            response.setEncoding('utf8');
            response.on('data', (chunk) => {
              data += chunk;
            });
            response.on('end', () => {
              var result = JSON.parse(data);
              if (cmd == 'user') {
                cb(result['user'] ? result : {'user': 0});
              } else if (cmd == 'captcha') {
                cb(result['captcha'] ? result : null);
              } else if (cmd.includes('report')) {
                cb(!result['is_correct']);
              } else {
                cb(result['captcha'] ? result : {'captcha': 0});
              };
            });
            break;
          case 403:
            throw new Error('Access denied, please check your credentials and/or balance');
            break;
          case 400:
          case 413:
            throw new Error('CAPTCHA was rejected by the service, check if i\'s a valid image');
            break;
          case 503:
            throw new Error('CAPTCHA was rejected due to service overload, try again later');
            break;
          default:
						console.log(response.statusCode);
            throw new Error('Invalid API response');
        };
      };
    });
  };

  get_user(cb) {
    const params = {
      'cmd': 'user',
      'payload': this.userpwd,
    };
    this._call(params, cb);
  };

  get_captcha(cid, cb) {
    // Fetch a captcha details -- ID, text and correctness flag.
    const params = {
      'cmd': 'captcha/' + cid,
    };
    this._call(params, cb);
  }

  report(cid, cb) {
    // Report a captcha as incorrectly solved.
    const params = {
      'cmd': 'captcha/' + cid + '/report',
      'payload': this.userpwd,
    };
    this._call(params, cb);
  };

  upload({captcha=null, extra={}}, cb) {

    // Upload a CAPTCHA.

    // Accept file names and file-like objects. Return CAPTCHA details
    // JSON on success.

    const banner = (extra.banner ? extra.banner : null);
    var files = {};
    if (captcha) {
      files['captchafile'] = 'base64:' + load_image(captcha);
    };
    if (banner) {
      files['banner'] = 'base64:' + load_image(banner);
    };
    var payload = this.userpwd;
    for (var entry in extra) {
      payload[entry] = extra[entry];
    }
    const params = {
      'cmd': 'captcha',
      'payload': payload,
      'files': files
    };
    this._call(params, cb);
  };

};

class SocketClient extends Client {

  // Death By Captcha Socket API Client.

  _call({cmd, payload={}, headers={}, files=null}, cb) {

    payload['cmd'] = cmd;
    payload['version'] = API_VERSION;

    const options = {
      host: HTTP_BASE_URL,
      port: getRandomInt(8123, 8130)
    };

    if (files) {
      for (var file_key in files) {
        payload[file_key] = files[file_key];
      };
    };

    const request = JSON.stringify(payload) + TERMINATOR;

    var need_login = (cmd != 'login');
    const login_request = JSON.stringify({
      'cmd': 'login',
      'username': payload['username'],
      'password': payload['password']
    }) + TERMINATOR;

    const socket = net.createConnection(options, () => {
      if (need_login) {
        socket.write(login_request, 'utf8');
      } else {
        socket.write(request, 'utf8');
      };
    });

    socket.on('error', (err) => {
			cb({}, err);
    });

    var data = '';
    socket.on('data', (chunk) => {
      data += chunk;
      if (data.includes(TERMINATOR)) {
        if (need_login) {
          need_login = false;
          data = '';
          socket.write(request, 'utf8');
        } else {
          socket.end();
          try {
            var result = JSON.parse(data.trimRight(TERMINATOR));
          } catch (err) {
            throw new Error('Invalid API response');
          }
          if (result['error']) {
            if (result['error'] == 'not-logged-in' || result['error'] == 'invalid-credentials') {
              throw new Error('Access denied, check your credentials');
            } else if (result['error'] == 'banned') {
              throw new Error('Access denied, account is suspended');
            } else if (result['error'] == 'insufficient-funds') {
              throw new Error('CAPTCHA was rejected due to low balance');
            } else if (result['error'] == 'invalid-captcha') {
              throw new Error('CAPTCHA is not a valid image');
            } else if (result['error'] == 'service-overload') {
              throw new Error('CAPTCHA was rejected due to service overload, try again later');
            } else {
              throw new Error('API server error ocurred: ' + result['error']);
            }
          } else {
            if (cmd == 'user') {
              cb(result['user'] ? result : {'user': 0});
            } else if (cmd == 'upload') {
              cb(result['captcha'] ? result : null);
            } else if (cmd.includes('report')) {
              cb(result['is_correct'] ? !result['is_correct'] : null);
            } else {
              cb(result['captcha'] ? result : {'captcha': 0});
            }
          }
        }
      }
    });
  };

  get_user(cb) {
    // Fetch user details -- ID, balance, rate and banned status.
    const params = {
      'cmd': 'user',
      'payload': this.userpwd,
    };
    this._call(params, cb);
  };

  get_captcha(cid, cb) {
    // Fetch a captcha details -- ID, text and correctness flag.
    const params = {
      'cmd': 'captcha',
      'payload': {
        'captcha': cid
      }
    };
    this._call(params, cb);
  };

  report(cid, cb) {
    // Report a captcha as incorrectly solved.
    const params = {
      'cmd': 'report',
      'payload': {
        'captcha': cid
      }
    };
    this._call(params, cb);
  };

  upload({captcha=null, extra={}}, cb) {

    // Upload a CAPTCHA.

    // Accept file names and file-like objects. Return CAPTCHA details
    // JSON on success.

    const banner = (extra.banner ? extra.banner : null);
    var files = {};
    if (captcha) {
      files['captcha'] = load_image(captcha);
    };
    if (banner) {
      files['banner'] = load_image(banner);
    };
    var payload = this.userpwd;
    for (var entry in extra) {
      if (entry != 'banner') {
        payload[entry] = extra[entry];
      };
    };
    const params = {
      'cmd': 'upload',
      'payload': payload,
      'files': files
    };
    this._call(params, cb);
  };

};

module.exports = {
  HttpClient: HttpClient,
  SocketClient: SocketClient
};

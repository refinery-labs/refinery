'use strict';
const https = require('https')
function log(data) {
    process.stdout.write(JSON.stringify(data));
}
function httpsPost({body, ...options}) {
    return new Promise((resolve,reject) => {
        const req = https.request({
            method: 'POST',
            ...options,
        }, res => {
            const chunks = [];
            res.on('data', data => chunks.push(data))
            res.on('end', () => {
                let body = Buffer.concat(chunks);
                switch(res.headers['content-type']) {
                    case 'application/json':
                        body = JSON.parse(body);
                        break;
                }
                resolve(body)
            })
        })
        req.on('error',reject);
        if(body) {
            req.write(body);
        }
        req.end();
    })
}
module.exports.handler = async event => {
    const workflowCallbackURL = new URL(process.env.WORKFLOW_CALLBACK_URL);
    const data = JSON.stringify(event.Records);
    
    const res = await httpsPost({
        hostname: workflowCallbackURL.host,
        path: workflowCallbackURL.pathname,
        port: workflowCallbackURL.port,
        headers: {
            'Content-Type': 'application/json',
            'Content-Length': data.length
        },
        body: data
    })
    
    log(res);
    return {};
};
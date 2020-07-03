#!/bin/bash

# Holy shit these plugins are so bad.
# There is no way to replace the path for the service worker to be on NOT A CDN IN THE CONFIG
# And because of this... The service worker breaks! So off to sed we go.
# https://github.com/vuejs/vue-cli/issues/3571
sed -i 's/https:\/\/d3asw1bke2pwdg.cloudfront.net\/manifest.json/\/manifest\/manifest.json/g' dist/index.html
sed -i 's/https:\/\/d3asw1bke2pwdg.cloudfront.net\/precache-manifest/\/manifest\/precache-manifest/g' dist/service-worker.js

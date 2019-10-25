const webpack = require('webpack');
const MonacoEditorPlugin = require('monaco-editor-webpack-plugin');

module.exports = {
  lintOnSave: false,
  publicPath: process.env.NODE_ENV === 'production' ? 'https://d3asw1bke2pwdg.cloudfront.net/' : '/',
  // integrity: true,
  css: {
    loaderOptions: {
      // pass options to sass-loader
      sass: {
        // @/ is an alias to src/
        // so this assumes you have a file named `src/variables.scss`
        data: `@import "~@/styles/variables.scss";`
      }
    }
  },
  chainWebpack: config => {
    // Skip loading hot loader
    if (process.env.NODE_ENV === 'production') {
      return;
    }

    config.module
      .rule(/\.(j|t)sx$/)
      .test(/\.(j|t)sx$/)
      .use('vue-jsx-hot-loader')
      .before('babel-loader')
      .loader('vue-jsx-hot-loader');
  },
  configureWebpack: {
    plugins: [
      new MonacoEditorPlugin(['javascript', 'php', 'python', 'go', 'json', 'markdown', 'ruby']),
      process.env.NODE_ENV === 'production' &&
        new webpack.SourceMapDevToolPlugin({
          // Local daemon address for retrieving sourcemaps from private S3 bucket.
          publicPath: 'https://localhost:8003/',
          filename: '[file].map'
        })
    ]
  },
  pwa: {
    // workboxPluginMode: 'InjectManifest',
    workboxPluginMode: 'GenerateSW',
    workboxOptions: {
      // swSrc: 'src/service-worker.js',
      swDest: 'service-worker.js',
      clientsClaim: true,
      skipWaiting: true,
      runtimeCaching: [
        {
          urlPattern: new RegExp('^https://app.refinery.io/api', 'i'),
          handler: 'networkOnly'
        },
        {
          urlPattern: new RegExp('.worker.js$', 'i'),
          handler: 'networkOnly'
        },
        {
          urlPattern: new RegExp('.(?:css|js|)$', 'i'),
          handler: 'networkFirst',
          options: {
            networkTimeoutSeconds: 30,
            cacheName: 'app',
            expiration: {
              maxAgeSeconds: 60 * 60 * 6
            }
          }
        },
        {
          urlPattern: new RegExp('.(?:png|gif|jpg|jpeg|svg)$', 'i'),
          handler: 'cacheFirst'
        },
        {
          urlPattern: new RegExp('^https://app.refinery.io/', 'i'),
          handler: 'networkFirst',
          options: {
            networkTimeoutSeconds: 30,
            cacheName: 'app',
            expiration: {
              maxAgeSeconds: 60 * 60 * 24
            }
          }
        }
      ]
    }
  },
  pluginOptions: {
    s3Deploy: {
      awsProfile: 'default',
      region: 'us-east-1',
      bucket: 'app.refinery.io',
      pwa: true,
      pwaFiles: 'index.html,service-worker.js,manifest.json',
      uploadConcurrency: 5,
      registry: undefined,
      createBucket: false,
      staticHosting: true,
      staticIndexPage: 'index.html',
      staticErrorPage: 'error.html',
      assetPath: 'dist',
      assetMatch: ['**', '!**/*.map'],
      deployPath: '/',
      acl: 'public-read',
      enableCloudfront: false,
      pluginVersion: '3.0.0'
    }
  }
};

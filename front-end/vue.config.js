module.exports = {
  lintOnSave: false,
  // Uncomment once the CDN stuff is finished
  // publicPath: process.env.NODE_ENV === 'production' ? 'https://d3asw1bke2pwdg.cloudfront.net/' : '/',
  integrity: true,
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
    config.module
      .rule(/\.(j|t)sx$/)
      .test(/\.(j|t)sx$/)
      .use('vue-jsx-hot-loader')
      .before('babel-loader')
      .loader('vue-jsx-hot-loader');
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
          urlPattern: new RegExp('.(?:css|js|)$', 'i'),
          handler: 'networkFirst'
        },
        {
          urlPattern: new RegExp('.(?:png|gif|jpg|jpeg|svg)$', 'i'),
          handler: 'cacheFirst'
        },
        {
          urlPattern: new RegExp('^https://app.refinery.io/', 'i'),
          handler: 'networkFirst',
          options: {
            networkTimeoutSeconds: 10,
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
      assetMatch: '**',
      deployPath: '/',
      acl: 'public-read',
      enableCloudfront: false,
      pluginVersion: '3.0.0'
    }
  }
};

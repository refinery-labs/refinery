module.exports = {
  lintOnSave: false,
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
    clientsClaim: true,
    skipWaiting: true,
    workboxPluginMode: 'InjectManifest',
    workboxOptions: {
      swSrc: 'service-worker.js'
      // runtimeCaching: [
      //   {
      //     urlPattern: /img/,
      //     handler: 'NetworkFirst',
      //     options: {
      //       // Fall back to the cache after 30 seconds.
      //       networkTimeoutSeconds: 10
      //     }
      //   },
      //   {
      //     urlPattern: /^/,
      //     handler: 'NetworkFirst',
      //     options: {
      //       // Fall back to the cache after 30 seconds.
      //       networkTimeoutSeconds: 30,
      //       expiration: {
      //         maxAgeSeconds: 85000
      //       }
      //     }
      //   }
      // ]
    }
  }
};

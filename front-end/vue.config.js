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
    runtimeCaching: [
      {
        urlPattern: /img/,
        handler: 'NetworkFirst',
        options: {
          // Fall back to the cache after 10 seconds.
          networkTimeoutSeconds: 10,
          expiration: {
            maxEntries: 5,
            maxAgeSeconds: 60
          }
        }
      },
      {
        urlPattern: new RegExp('^'),
        handler: 'NetworkOnly'
      }
    ]
  }
};

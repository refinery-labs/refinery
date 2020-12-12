const webpack = require('webpack');
const MonacoEditorPlugin = require('monaco-editor-webpack-plugin');

const aliases = {};
const transpileDependencies = [];

const cloudfrontURL = process.env.CLOUDFRONT_URL; // 'https://d3asw1bke2pwdg.cloudfront.net/'
const s3DeployRegion = process.env.S3_DEPLOY_REGION;  // 'us-east-1'
const s3DeployBucket = process.env.S3_DEPLOY_BUCKET;  // 'app.refinery.io' or 'app-staging.refinery.io'
const s3DeployPath = process.env.S3_DEPLOY_PATH;  // '/' or '/staging'
const appAPIURL = process.env.VUE_APP_API_HOST;        // https://app.refinery.io/

// General plugins for all environments
const plugins = [
  new MonacoEditorPlugin({
    filename: '[name]-[hash].worker.js',
    publicPath: '/',
    languages: ['javascript', 'php', 'python', 'go', 'json', 'markdown', 'ruby']
  })
];

// These plugins are for only production
if (process.env.NODE_ENV === 'production') {
  plugins.push(
    new webpack.SourceMapDevToolPlugin({
      // Local daemon address for retrieving sourcemaps from private S3 bucket.
      publicPath: 'https://localhost:8003/',
      filename: '[file].map[query]'
    })
  );
}

module.exports = {
  lintOnSave: false,
  publicPath: process.env.NODE_ENV === 'production' ? cloudfrontURL : '/',
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
      // config.output.chunkFilename(`js/[name].[id].[chunkhash:8].js`);
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
    plugins,
    optimization: {
      splitChunks: {
        chunks: 'all',
        cacheGroups: {
          monaco: {
            test: /[\\/]node_modules[\\/](monaco-editor|monaco-editor-webpack-plugin)/,
            name: 'monaco',
            priority: -5,
            reuseExistingChunk: true
          },
          jsYaml: {
            test: /[\\/]node_modules[\\/]js-yaml/,
            name: 'js-yaml',
            priority: -5,
            reuseExistingChunk: true
          },
          git: {
            test: /[\\/]node_modules[\\/]isomorphic-git/,
            name: 'isomorphic-git',
            priority: -5,
            reuseExistingChunk: true
          },
          markdown: {
            test: /[\\/]node_modules[\\/](vue-markdown|uslug)/,
            name: 'markdown',
            priority: -5,
            reuseExistingChunk: true
          },
          jszip: {
            test: /[\\/]node_modules[\\/]jszip/,
            name: 'jszip',
            priority: -5,
            reuseExistingChunk: true
          },
          bootstrapVue: {
            test: /[\\/]node_modules[\\/]bootstrap-vue/,
            name: 'bootstrap-vue',
            priority: -25,
            reuseExistingChunk: true
          },
          vendors: {
            reuseExistingChunk: true
            // chunks: 'all'
          },
          common: {
            reuseExistingChunk: true,
            chunks: 'all'
          }
        }
        // minSize: 10000,
        // maxSize: 250000
      }
    },
    resolve: {
      alias: aliases
    }
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
          urlPattern: new RegExp(`^${appAPIURL}/api`, 'i'),
          handler: 'NetworkOnly'
        },
        {
          urlPattern: new RegExp('.worker.js$', 'i'),
          handler: 'NetworkOnly'
        },
        {
          urlPattern: new RegExp('.(?:css|js|)$', 'i'),
          handler: 'NetworkFirst',
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
          handler: 'CacheFirst'
        },
        {
          urlPattern: new RegExp(`^${appAPIURL}`, 'i'),
          handler: 'CacheFirst',
          options: {
            cacheName: 'app',
            expiration: {
              maxAgeSeconds: 60 * 60 * 24
            }
          }
        },
        {
          urlPattern: new RegExp(`^${cloudfrontURL}`, 'i'),
          handler: 'CacheFirst'
        }
      ]
    }
  },
  pluginOptions: {
    s3Deploy: {
      awsProfile: 'default',
      region: s3DeployRegion,
      bucket: s3DeployBucket,
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
      deployPath: s3DeployPath,
      acl: 'public-read',
      enableCloudfront: false,
      pluginVersion: '3.0.0'
    }
  },
  transpileDependencies
};

module.exports = {
  lintOnSave: false,
  css: {
    // modules: true,
    loaderOptions: {
      // pass options to sass-loader
      sass: {
        // @/ is an alias to src/
        // so this assumes you have a file named `src/variables.scss`
        data: `@import "~@/styles/variables.scss";`,
        // includePaths: [
        //   path.resolve(__dirname, 'src/styles/')
        // ],
      }
    }
  }
};

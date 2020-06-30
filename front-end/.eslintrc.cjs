module.exports = {
  root: true,
  env: {
    node: true
  },
  extends: ['plugin:vue/essential', '@vue/prettier', '@vue/typescript'],
  rules: {
    'no-console': process.env.NODE_ENV === 'production' ? 'error' : 'off',
    'no-debugger': process.env.NODE_ENV === 'production' ? 'error' : 'off',
    eqeqeq: 'error',
    quotes: ['error', 'single', { allowTemplateLiterals: true, avoidEscape: true }],
    'prettier/prettier': ['error', { singleQuote: true, printWidth: 120 }]
  },
  parserOptions: {
    parser: '@typescript-eslint/parser'
  }
};

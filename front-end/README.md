# refinery-front-end

## Code Philosophy

- Use Typescript or fear eternally for your production (and mental) stability
- Follow "separation of concerns" in code that you write.
  - If you have to think "should this go in this file?" the answer is probably no.
- Either use the `utils` or the `lib` folder for code that doesn't clearly fit somewhere.
  - The differences between utils and lib are:
    - `lib` you can imagine as "staging" for a future npm module. Put code here that isn't specific to refinery, but that we wrote. The URL sanitizer is an example.
    - `utils` are functions that are business logic for the repo. They may be shared across files one day and they would never leave the repo.
- Use Vuex instead of local state, unless you have a good reason!
- Laziness is a virtue but don't be lazy now. The truly lazy do work up front, since they will probably forget otherwise.

## Project setup
```
npm install
```

### Compiles and hot-reloads for development
```
npm run serve
```

### Compiles and minifies for production
```
npm run build
```

### Run your tests
```
npm run test
```

### Lints and fixes files
```
npm run lint
```

### Run your end-to-end tests
```
npm run test:e2e
```

### Run your unit tests
```
npm run test:unit
```

### Customize configuration
See [Configuration Reference](https://cli.vuejs.org/config/).

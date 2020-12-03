# refinery-front-end

test

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


## Debugging

Useful debugging tool for Typescript stuff is the Babel live transpiler.
[Link](https://babeljs.io/en/repl#?babili=false&browsers=&build=&builtIns=false&spec=false&loose=false&code_lz=JYWwDg9gTgLgBAbzgYSgUwIYzQUQDZohoB2MANHAGoByEAJmnAL5wBmUEIcA5AG4CuabgG4AUKEixEKTpGIlycAAocwFSoOZsOXPoIC0YVWlgBPfQwDG0LNBHjw0eAjwZiAc34Z3aACoQAQUs0ABk3dwBZDDAWdk4eAAEAehhTMDQAZySjCAArNEsYfTQ6YBhofVT0jPsJJzgg3FLyqG147mTrR3lSLOROEAhiJMacZugAOgEhMTqpBDGy6BUIMAzYnUSUtMykrrkFSp2asVEE_u6FUUtXDIy4ACU0VmB5KFN-hkWWuDQAD2wxDo9w0jAQojgcASKzAAAokOgAI78YDoOgALjgMCgmiYAEo4EZgLwsIwSksoDCMgBCTHfZaqe4AHzgxH4eDwp0hYH4ACM8MBLHB0ECTPSoLCCeDIZDrMQMvAcms4ABeLEAC2AGQm5JaVK5MqSSTgAElWHAAO6MOhDbjwdUYXiMEkCuhwBWkijYDkaxj8DImCYQmXAc2w6lKjJS4My4VoGD8KDEOCwmOxuAAHnVAGYAHz9dlu4gQeClDJgVymODWBi_cZQCYZpI53NpyF4sSxpiiNNGuC-dWMABE6AVQ7gWt-TveME1Hl-f2CYHgwDdbjdrg8E1NMG49yHs8Yo5g44g5sPcAgvPyhSDsblCsQq4om_cFAmH-PLDVkYNkL7A6TpOGT8OkrTuBwdxwLy_DwO4QzEBgcAEI6jBlGw0CshAFrbjgTqkF4HJVrCoaWowGB0GucAAExAgSVqWsAPryCUWIQHANpwG4cA4GyXB4BAEAANagb2xohMAQnDpOs5AcmF4kPwIDjq8l5QAwrSsJhF4gNEYCvO4bGWtAQnbr4xyWFAwDLoxPqmGgPoZOxxbwBg7AYKucDoniaYPvAurQGEHheD4qrIeEqoqmqdr_LucAAPw8NgALcF54XBd4fiBMEQWRNEADar4ALp_tWQyPhgwRUmF0rptwAVQPoq7cJiAAGDX6DixD6K4IC8nQGBNcQPJFAAJAgq5MK1ZBtr6RCYtwgzFkJHncDN6bpe4mINblIVoOt6YfhMx5pkwpXoAmSYprNfYJDAGRNe4xboLNGajPWs2Qh1q4qgglVoFS-X1fWTV0NwRXdhtkKvr9_1UhMr6Q1Dh5ELDVWMhMKNoEjG1yoCMBowDGN4woOPpkMhPw0MZP_q2sYdsG3bBjy_KCnGooSuqmKoJg2D4IQCh4piND0GCaYXYmyaphtGalLw1a3BkKojs8rwmOYNZoMUIN4x5byMXQs76PoACMAAMZtgcEpBDnTUMILJ2oihp4qSjTmZJHLdvtp2zCiEz_ySKWzwYOy8BPC8bwfKL4piEAA&debug=false&forceAllTransforms=false&shippedProposals=false&circleciRepo=&evaluate=false&fileSize=false&timeTravel=false&sourceType=module&lineWrap=true&presets=es2017%2Cstage-2%2Cstage-3%2Ctypescript&prettier=true&targets=Node-8.9&version=7.4.5&externalPlugins=%40babel%2Fplugin-transform-typescript%407.4.5%2Cbabel-plugin-transform-vue-jsx%403.7.0)

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

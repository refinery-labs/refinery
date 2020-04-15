#!/bin/bash

./node_modules/.bin/typescript-json-validator --strictNullChecks src/types/export-project.ts ImportableRefineryProject

./node_modules/.bin/typescript-json-validator --strictNullChecks --useNamedExport src/repo-compiler/shared/types.ts RefineryGitProjectConfig


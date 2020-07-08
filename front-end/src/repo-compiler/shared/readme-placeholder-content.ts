import { RefineryProject } from '@/types/graph';

export function getPlaceholderReadmeContent(project: RefineryProject, gitURL: string) {
  const shareRepoByURLLink = `${process.env.VUE_APP_API_HOST}/import?i=${project.project_id}&r=${gitURL}`;
  return `
# ${project.name}

Generated from compiling a [refinery.io](https://refinery.io) project.

## Deploy

[<img src="https://github-documentation.s3.amazonaws.com/REF-deploy-button-purple.png">](${shareRepoByURLLink})

In order to deploy this project, you must go to the project page on [refinery.io](https://refinery.io):

1. Login to your account on https://app.refinery.io
2. Open project configured to use this repository
3. Click "Deploy Project"

## Documentation

For understanding how Code Blocks and other types of blocks and transitions work, check out the [docs](https://docs.refinery.io/getting-started/).

### Folder Layout

\`\`\`
refinery/
  lambda/
    ...
  projects/
    ...
  shared-files/
    ...
\`\`\`


#### Code Blocks

\`lambda\` contains all Code Blocks which are used by the project. Each folder contains the following files:

\`\`\`
shared_files/
  ...
block_code.[ext]
config.yaml
input_config.yaml
[dependencies file]
run_code.[ext]
run_code.sh
\`\`\`

* \`shared-files\` holds symbolic links to files located in the \`shared-files\` folder in the root \`refinery\` folder.
* \`block_code.[ext]\` contains the code which will be run in this Code Block. 
* \`config.yaml\` configuration for the Code Block.
* \`input_config.yaml\` configuration for the Code Block's input when testing the block locally.
* \`[dependencies file]\` this is a generated file specifically for the Code Block's language and includes any configured libraries required by the Code Block (ex. if the language is nodejs, this file will be named \`package.json\` and the block's dependencies can be installed with running \`npm install\`).
* \`run_code.[ext]\` contains bootstrap code required in order to mimic how the block will behave when deployed.
* \`run_code.sh\` can be used to run the Code Block locally once the local development environment has been set up.

#### Projects

\`projects\` holds the project configuration, named by its identifier. You may change the contents of this file and it will be reflected in the project.

NOTE: Currently you can only store one project in a git repository. Multiple projects per git repository will be supported soon.

#### Shared Files

\`shared-files\` contains all shared files used by Code Blocks.

### Running Code Blocks Locally

All Code Blocks associated with the project are located in \`lambda\` folder and can be run locally.

To run a Code Block locally, make sure you have your development environment setup to run the Code Block's language (ex. if the block you want to run is written in the \`Python\` language, the \`python\` executable must runnable from your terminal.)

All of the Code Block's libraries must also be installed, you can install these from the included .

Once your development environment is setup, to run the Code Block code, run \`sh run_code.sh\`.

[![asciicast](https://asciinema.org/a/344164.svg)](https://asciinema.org/a/344164)

To modify \`input\` or \`backpack\` data which is being passed into the Code Block, modify the YAML configuration for the block in  \`block_config.yaml\`.

[![asciicast](https://asciinema.org/a/344165.svg)](https://asciinema.org/a/344165)
`;
}

export function getPlaceholderReadmeContent(projectName: string) {
  return `
# ${projectName} 

Generated from [refinery.io](https://refinery.io).

This repository contains a compiled version of a Refinery project in the \`refinery/\` folder.

## Documentation

For getting started, check out the [docs](https://docs.refinery.io/getting-started/)

### Folder Layout

\`\`\`
refinery/
  blocks/
    ...
  projects/
    ...
  shared-files/
    ...
\`\`\`


#### Code Blocks

\`blocks\` contains all Code Blocks which are used by the project. Each folder contains the following files:

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

\`shared-files\` holds symbolic links to files located in the \`shared-files\` folder in the root \`refinery\` folder.
\`block_code.[ext]\` contains the code which will be run in this Code Block. 
\`config.yaml\` configuration for the Code Block.
\`input_config.yaml\` configuration for input 

#### Projects

\`projects\`

#### Shared Files

\`shared-files\`

### Running Code Blocks Locally

All Code Blocks associated with the project are located in \`lambda\` folder and can be run locally.

To run a Code Block locally, make sure you have your development environment setup to run the Code Block's language (ex. if the block you want to run is written in the \`Python\` language, the \`python\` executable must runnable from your terminal.)

All of the Code Block's libraries must also be installed, you can install these from the included .

Once your development environment is setup, to run the Code Block code, run \`sh run_code.sh\`.

To modify \`input\` or \`backpack\` data which is being passed into the Code Block, modify the YAML configuration for the block in  \`block_config.yaml\`.

## Deploy

1. Login to your account on https://app.refinery.io
2. Open project configured to use this repository
3. Click "Deploy Project"
`;
}

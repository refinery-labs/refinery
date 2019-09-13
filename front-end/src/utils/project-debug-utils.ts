import JSZip from 'jszip';
import { saveAs } from 'file-saver';
import { LambdaWorkflowState, RefineryProject, SupportedLanguage } from '@/types/graph';

export interface ZippableFileContents {
  fileName: string;
  contents: string;
}

export interface ProjectDownloadZipMetadata {
  projectName: string;
  projectId: string;
  projectVersion: number;
  blockName: string;
  blockId: string;
  exportedTimestamp: number;
  version: string;
}

export interface ProjectDownloadZipConfig {
  inputData: string;
  backpackData: string;
  blockCode: string;
  blockLanguage: SupportedLanguage;
  metadata: ProjectDownloadZipMetadata;
}

export type ZippableFileList = ZippableFileContents[];

export type LanguageToStringLookup = { [key in SupportedLanguage]: string };

export const languageToRunScriptLoopup: LanguageToStringLookup = {
  [SupportedLanguage.NODEJS_8]: 'node block-code.js',
  [SupportedLanguage.PYTHON_3]: 'python block-code.py',
  [SupportedLanguage.PYTHON_2]: 'python block-code.py',
  [SupportedLanguage.GO1_12]: 'go run block-code.go',
  [SupportedLanguage.PHP7]: 'php -f block-code.php',
  [SupportedLanguage.RUBY2_6_4]: 'ruby block-code.rb'
};

export const languageToFileExtension: LanguageToStringLookup = {
  [SupportedLanguage.NODEJS_8]: 'js',
  [SupportedLanguage.PYTHON_3]: 'py',
  [SupportedLanguage.PYTHON_2]: 'py',
  [SupportedLanguage.GO1_12]: 'go',
  [SupportedLanguage.PHP7]: 'php',
  [SupportedLanguage.RUBY2_6_4]: 'rb'
};

const pythonPrependedCode = `
# Start of Refinery Generated Code
import traceback
import json
import sys
# End of Refinery Generated Code
`;

export const languageToPrependedCode: LanguageToStringLookup = {
  [SupportedLanguage.NODEJS_8]: '// This file was partially generated by Refinery',
  [SupportedLanguage.PYTHON_3]: pythonPrependedCode,
  [SupportedLanguage.PYTHON_2]: pythonPrependedCode,
  [SupportedLanguage.GO1_12]: '// This file was partially generated by Refinery',
  [SupportedLanguage.PHP7]: '// This file was partially generated by Refinery',
  [SupportedLanguage.RUBY2_6_4]: '# This file was partially generated by Refinery'
};

const pythonAppendedCode = `
# Begin Refinery Generated Code
with open('input-data.json') as input_data_raw:
  input_data = json.load(input_data_raw)
  
  # Set to default of string
  if "data" not in input_data:
    input_data["data"] = ""

with open('backpack-data.json') as backpack_data_raw:
  backpack_data = json.load(backpack_data_raw)

output_data = main(input_data["data"], backpack_data)

print(json.dumps(output_data, indent=2))
# End Refinery Generated Code
`;

export const languageToAppendedCode: LanguageToStringLookup = {
  [SupportedLanguage.NODEJS_8]: `
// Begin Refinery Generated Code
const inputData = require('./input-data.json');
const backpackData = require('./backpack-data.json');

if (typeof main !== undefined) {
  async function runMainAsync() {
    try {
      const outputData = await main(inputData.data, backpackData);
      console.log(JSON.stringify(outputData, null, 2));
    } catch (e) {
      console.error(JSON.stringify(e, null, 2));
      throw new Error(e);
    }
  }

  runMainAsync();

} else if (typeof mainCallback !== undefined) {
  mainCallback(inputData.data, backpackData, (err, outputData) => {
    if (err) {
      console.error(JSON.stringify(e, null, 2));
      throw new Error(e);
    }
   
    console.log(JSON.stringify(outputData, null, 2)); 
  });
} else {
  throw new Error('No entrypoint defined');
}
// End Refinery Generated Code
`,
  [SupportedLanguage.PYTHON_3]: pythonAppendedCode,
  [SupportedLanguage.PYTHON_2]: pythonAppendedCode,
  [SupportedLanguage.GO1_12]:
    '\n// Not supported yet. Read input-data.json and backpack-data.json then call main().\nAlso email support@refinery.io and we will add this. :)',
  [SupportedLanguage.PHP7]:
    '\n// Not supported yet. Read input-data.json and backpack-data.json then call main().\nAlso email support@refinery.io and we will add this. :)',
  [SupportedLanguage.RUBY2_6_4]:
    '\n# Not supported yet. Read input-data.json and backpack-data.json then call main().\nAlso email support@refinery.io and we will add this. :)'
};

export function convertProjectDownloadZipConfigToFileList(config: ProjectDownloadZipConfig) {
  const zippableFiles: ZippableFileList = [];

  zippableFiles.push({
    fileName: 'input-data.json',
    contents: config.inputData
  });

  zippableFiles.push({
    fileName: 'backpack-data.json',
    contents: config.backpackData
  });

  zippableFiles.push({
    fileName: `block-code.${languageToFileExtension[config.blockLanguage]}`,
    contents:
      languageToPrependedCode[config.blockLanguage] + config.blockCode + languageToAppendedCode[config.blockLanguage]
  });

  zippableFiles.push({
    fileName: `run-code.sh`,
    contents: languageToRunScriptLoopup[config.blockLanguage]
  });

  zippableFiles.push({
    fileName: 'metadata.json',
    contents: JSON.stringify(config.metadata, null, 2)
  });

  return zippableFiles;
}

/*
## Contents:
input-data.json
backpack-data.json
run-code.sh
block-code.py
metadata.json
 */

export async function createProjectDownloadZip(config: ProjectDownloadZipConfig) {
  const zip = JSZip();

  const filesToZip = convertProjectDownloadZipConfigToFileList(config);

  filesToZip.forEach(file => zip.file(file.fileName, file.contents));

  const zippedContents = await zip.generateAsync<'blob'>({
    type: 'blob'
  });

  const zipName = `refinery-${config.metadata.projectName}-${config.metadata.blockName}-${Date.now()}.zip`.replace(
    / /g,
    '_'
  );

  saveAs(zippedContents, zipName);
}

export function createDownloadZipConfig(
  project: RefineryProject,
  block: LambdaWorkflowState
): ProjectDownloadZipConfig {
  return {
    inputData: JSON.stringify({ data: block.saved_input_data }, null, 2),
    backpackData: '{}',
    blockCode: block.code,
    blockLanguage: block.language,
    metadata: {
      blockName: block.name,
      blockId: block.id,
      projectName: project.name,
      projectId: project.project_id,
      projectVersion: project.version,
      exportedTimestamp: Date.now(),
      version: '1.0.0'
    }
  };
}

export async function downloadBlockAsZip(project: RefineryProject, block: LambdaWorkflowState) {
  const downloadZipConfig = createDownloadZipConfig(project, block);

  await createProjectDownloadZip(downloadZipConfig);
}
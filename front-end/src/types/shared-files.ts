export interface AddSharedFileArguments {
  name: string;
  body: string;
}

export interface AddSharedFileLinkArguments {
  // UUID of the workflow_file node
  file_id: string;
  // UUID of the Code Block workflow_state
  node: string;
  // Path where the file is written to relative
  // to the base directory (/var/task).
  // "" indicates the base directory.
  path: string;
}

export enum FileNodeMetadataTypes {
  sharedFileLink = 'sharedFileLink',
  codeBlock = 'codeBlock'
}

export interface FileNodeMetadata {
  id: string;
  type: FileNodeMetadataTypes;
}

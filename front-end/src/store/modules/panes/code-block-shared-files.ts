import { Action, getModule, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { RootState } from '../../store-types';
import { deepJSONCopy } from '@/lib/general-utils';
import store from '@/store';
import { resetStoreState } from '@/utils/store-utils';
import { LambdaWorkflowState, WorkflowFile, WorkflowFileLink, WorkflowRelationshipType } from '@/types/graph';
import { ProjectViewActions } from '@/constants/store-constants';
import { PANE_POSITION, SIDEBAR_PANE } from '@/types/project-editor-types';
import { EditSharedFilePaneModule } from '@/store/modules/panes/edit-shared-file';
import { AddSharedFileLinkArguments, FileNodeMetadata, FileNodeMetadataTypes } from '@/types/shared-files';
import { getSharedFileById, getSharedFilesForCodeBlock } from '@/utils/project-helpers';
import { ISlTreeNodeModel } from 'sl-vue-tree';
import { languageToFileExtension } from '@/utils/project-debug-utils';

const storeName = 'codeBlockSharedFiles';

// Types
export interface CodeBlockSharedFilesPaneState {
  codeBlock: LambdaWorkflowState | null;
}

// Initial State
const moduleState: CodeBlockSharedFilesPaneState = {
  codeBlock: null
};

const initialState = deepJSONCopy(moduleState);

export function getFileNodeFromSharedFileId(sharedFile: WorkflowFile): ISlTreeNodeModel<FileNodeMetadata> {
  return {
    title: sharedFile.name,
    isLeaf: true,
    isDraggable: false,
    data: {
      id: sharedFile.id,
      type: FileNodeMetadataTypes.sharedFileLink
    }
  };
}

@Module({ namespaced: true, dynamic: true, store, name: storeName })
class CodeBlockSharedFilesPaneStore extends VuexModule<ThisType<CodeBlockSharedFilesPaneState>, RootState>
  implements CodeBlockSharedFilesPaneState {
  public codeBlock: LambdaWorkflowState | null = initialState.codeBlock;

  get sharedFilesNotAlreadyInCodeBlock() {
    if (
      this.codeBlock === null ||
      this.context.rootState.project === null ||
      this.context.rootState.project.openedProject === null
    ) {
      return [];
    }

    const sharedFileIdsAlreadyInCodeBlock = getSharedFilesForCodeBlock(
      this.codeBlock.id,
      this.context.rootState.project.openedProject
    ).map(sharedFile => sharedFile.id);

    return this.context.rootState.project.openedProject.workflow_files.filter(
      workflowFile => !sharedFileIdsAlreadyInCodeBlock.includes(workflowFile.id)
    );
  }

  get fileNodes(): ISlTreeNodeModel<FileNodeMetadata>[] {
    // First we get the Shared Files for the current code block
    if (
      this.codeBlock === null ||
      this.context.rootState.project === null ||
      this.context.rootState.project.openedProject === null
    ) {
      return [];
    }

    const sharedFiles = getSharedFilesForCodeBlock(this.codeBlock.id, this.context.rootState.project.openedProject);

    return sharedFiles.map(sharedFile => getFileNodeFromSharedFileId(sharedFile));
  }

  get blockFileSystemTree(): ISlTreeNodeModel<FileNodeMetadata>[] {
    const rawFileNodes = CodeBlockSharedFilesPaneModule.fileNodes;

    // Gets only the valid file nodes and casts for the type system.
    const fileNodes = rawFileNodes.filter(n => n !== null) as ISlTreeNodeModel<FileNodeMetadata>[];

    if (CodeBlockSharedFilesPaneModule.codeBlock === null) {
      console.error('No Code Block is selected!');
      return [];
    }

    const baseLambdaFileExtension = languageToFileExtension[CodeBlockSharedFilesPaneModule.codeBlock.language];
    const baseLambdaFileName = `lambda.${baseLambdaFileExtension} (Code Block Script)`;

    return [
      {
        title: 'Base Folder (/var/task/)',
        isSelectable: false,
        isDraggable: false,
        isExpanded: true,
        children: [
          {
            title: baseLambdaFileName,
            isLeaf: true,
            isSelectable: false,
            isDraggable: false,
            data: {
              id: CodeBlockSharedFilesPaneModule.codeBlock.id,
              type: FileNodeMetadataTypes.codeBlock
            }
          },
          {
            title: 'shared_files/',
            isExpanded: true,
            isSelectable: false,
            isDraggable: false,
            children: fileNodes
          }
        ]
      }
    ];
  }

  @Mutation
  public resetState() {
    resetStoreState(this, initialState);
  }

  @Mutation
  public setCodeBlock(codeBlock: LambdaWorkflowState) {
    this.codeBlock = deepJSONCopy(codeBlock);
  }

  @Action
  public selectedFileTreeNode(fileNodeMetadata: FileNodeMetadata | null) {
    if (fileNodeMetadata === null) {
      console.error('Selected file tree node is null, quitting out.');
      return;
    }

    // If it's the lambda.EXT then we open the Code Block
    if (fileNodeMetadata.type === FileNodeMetadataTypes.codeBlock) {
      return this.context.dispatch(`project/${ProjectViewActions.selectNode}`, fileNodeMetadata.id, {
        root: true
      });
    }

    // Must be a shared file
    if (fileNodeMetadata.type !== FileNodeMetadataTypes.sharedFileLink) {
      return;
    }

    // Get shared file
    const sharedFile = getSharedFileById(fileNodeMetadata.id, this.context.rootState.project);

    // If it's null, drop out.
    if (sharedFile === null) {
      return;
    }

    // Set the shared file.
    EditSharedFilePaneModule.openSharedFile(sharedFile);
  }

  @Action
  public async openCodeBlockSharedFiles(codeBlock: LambdaWorkflowState) {
    this.setCodeBlock(codeBlock);
    EditSharedFilePaneModule.setCurrentSharedFilePane(SIDEBAR_PANE.codeBlockSharedFiles);
  }

  @Action
  public async addSharedFileToCodeBlock(sharedFile: WorkflowFile) {
    if (CodeBlockSharedFilesPaneModule.codeBlock === null) {
      console.error('No Code Block is selected.');
      return;
    }

    const addSharedFileLinkArgs = {
      file_id: sharedFile.id,
      node: CodeBlockSharedFilesPaneModule.codeBlock.id,
      path: ''
    };

    return this.context.dispatch(`project/${ProjectViewActions.addSharedFileLink}`, addSharedFileLinkArgs, {
      root: true
    });
  }
}

export const CodeBlockSharedFilesPaneModule = getModule(CodeBlockSharedFilesPaneStore);

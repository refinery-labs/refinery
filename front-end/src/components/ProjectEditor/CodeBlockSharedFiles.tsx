import Component from 'vue-class-component';
import Vue, { CreateElement, VNode } from 'vue';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import { EditSharedFilePaneModule } from '@/store/modules/panes/edit-shared-file';
import { EditSharedFileLinksPaneModule } from '@/store/modules/panes/edit-shared-file-links';
import { availableBlocks, blockTypeToImageLookup } from '@/constants/project-editor-constants';
import {
  LambdaWorkflowState,
  ProjectConfig,
  RefineryProject,
  WorkflowFile,
  WorkflowFileLink,
  WorkflowState
} from '@/types/graph';
import { namespace, Mutation, State } from 'vuex-class';
import { deepJSONCopy } from '@/lib/general-utils';
import { CodeBlockSharedFilesPaneModule } from '@/store/modules/panes/code-block-shared-files';
import { languageToFileExtension } from '@/utils/project-debug-utils';
import { PANE_POSITION, SIDEBAR_PANE } from '@/types/project-editor-types';
import ViewSharedFileLinkPane, {
  ViewSharedFileLinkProps
} from '@/components/ProjectEditor/shared-files-components/ViewSharedFilesList';
import { getSharedFilesForCodeBlock } from '@/utils/project-helpers';
import { AddSharedFileLinkArguments, FileNodeMetadata, FileNodeMetadataTypes } from '@/types/shared-files';

const project = namespace('project');

@Component
export default class CodeBlockSharedFilesPane extends Vue {
  @Mutation setCodeBlock!: (codeBlock: LambdaWorkflowState) => void;
  @project.Action selectNode!: (nodeId: string) => void;
  @project.Action addSharedFileLink!: (addSharedFileLinkArgs: AddSharedFileLinkArguments) => void;
  @project.State openedProject!: RefineryProject | null;

  getSharedFileById(fileId: string) {
    if (this.openedProject === null) {
      return null;
    }

    return deepJSONCopy(this.openedProject.workflow_files).filter(workflow_file => workflow_file.id === fileId)[0];
  }

  getFileNodeFromSharedFileId(sharedFileLink: WorkflowFileLink) {
    const sharedFile = this.getSharedFileById(sharedFileLink.file_id);

    if (sharedFile === null) {
      return null;
    }

    return {
      title: sharedFile.name,
      isLeaf: true,
      isDraggable: false,
      isLead: true,
      data: {
        id: sharedFileLink.file_id,
        type: FileNodeMetadataTypes.sharedFileLink
      } as FileNodeMetadata
    };
  }

  getBlockFileSystemTree() {
    const sharedLinks = this.getSharedLinksForCodeBlock();
    const fileNodes = sharedLinks.map(sharedFileLink => {
      return this.getFileNodeFromSharedFileId(sharedFileLink);
    });

    if (CodeBlockSharedFilesPaneModule.codeBlock === null) {
      console.error('No Code Block is selected!');
      return [];
    }

    const baseLambdaFileExtension = languageToFileExtension[CodeBlockSharedFilesPaneModule.codeBlock.language];
    const baseLambdaFileName = 'lambda.' + baseLambdaFileExtension + ' (Code Block Script)';

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
            } as FileNodeMetadata
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

  selectedFolder(event: any) {
    const fileNodeMetadata = event.data as FileNodeMetadata | null;

    if (fileNodeMetadata === null) {
      return;
    }

    // If it's the lambda.EXT then we open the Code Block
    if (fileNodeMetadata.type === FileNodeMetadataTypes.codeBlock) {
      this.selectNode(fileNodeMetadata.id);
    }

    // If it's a Shared File, we'll open it.
    if (fileNodeMetadata.type === FileNodeMetadataTypes.sharedFileLink) {
      // Get shared file
      const sharedFile = this.getSharedFileById(fileNodeMetadata.id);

      if (sharedFile !== null) {
        // Set the shared file.
        EditSharedFilePaneModule.openSharedFile(sharedFile);
      }
    }
  }

  getSharedLinksForCodeBlock() {
    if (this.openedProject === null || CodeBlockSharedFilesPaneModule.codeBlock === null) {
      return [];
    }

    return deepJSONCopy(this.openedProject.workflow_file_links).filter(workflow_file_link => {
      // Can't actually be null, TypeScript is wrong?
      // @ts-ignore
      return workflow_file_link.node === CodeBlockSharedFilesPaneModule.codeBlock.id;
    });
  }

  addSharedFileToCodeBlock(sharedFile: WorkflowFile) {
    if (CodeBlockSharedFilesPaneModule.codeBlock === null) {
      console.error('No Code Block is selected!');
      return;
    }

    const addSharedFileLinkArgs: AddSharedFileLinkArguments = {
      file_id: sharedFile.id,
      node: CodeBlockSharedFilesPaneModule.codeBlock.id,
      path: ''
    };

    this.addSharedFileLink(addSharedFileLinkArgs);
  }

  public render(h: CreateElement): VNode {
    if (this.openedProject === null || CodeBlockSharedFilesPaneModule.codeBlock === null) {
      return <div>No project is opened!</div>;
    }

    const treeProps = {
      value: this.getBlockFileSystemTree()
    };

    const sharedFiles = getSharedFilesForCodeBlock(CodeBlockSharedFilesPaneModule.codeBlock.id, this.openedProject);

    const viewSharedFileLinkPaneProps: ViewSharedFileLinkProps = {
      sharedFileClickHandler: this.addSharedFileToCodeBlock,
      sharedFilesText: 'All Shared Files (click to add to Code Block): ',
      sharedFilesArray: sharedFiles
    };

    return (
      <div class="text-align--left ml-2 mr-2 mt-0 display--flex flex-direction--column shared-file-links-pane">
        <b-form-group>
          <b-list-group-item class="display--flex">
            <img class="add-block__image" src={require('../../../public/img/node-icons/code-icon.png')} />
            <div class="flex-column align-items-start add-block__content">
              <div class="d-flex w-100 justify-content-between">
                <h4 class="mb-1 mt-3">
                  {CodeBlockSharedFilesPaneModule.codeBlock
                    ? CodeBlockSharedFilesPaneModule.codeBlock.name
                    : 'No Code Block Selected!'}
                </h4>
              </div>
              <p class="mb-1">You are currently viewing this Code Block's Shared Files.</p>
            </div>
          </b-list-group-item>
        </b-form-group>

        <b-form-group description="This is a file view of this Code Block's Shared Files. All shared files are placed in the shared_files directory.">
          <div class="display--flex flex-wrap mb-1">
            <label class="d-block flex-grow--1 pt-1">Code Block's Files (click a file to open it):</label>
          </div>
          <sl-vue-tree props={treeProps} on={{ nodeclick: this.selectedFolder }} />
        </b-form-group>

        <h4>Add Shared File to Code Block</h4>
        <ViewSharedFileLinkPane props={viewSharedFileLinkPaneProps} />
      </div>
    );
  }
}

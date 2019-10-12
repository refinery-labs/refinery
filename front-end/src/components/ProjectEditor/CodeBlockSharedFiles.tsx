import Component from 'vue-class-component';
import Vue, { CreateElement, VNode } from 'vue';
import { EditSharedFilePaneModule } from '@/store/modules/panes/edit-shared-file';
import { LambdaWorkflowState, RefineryProject, WorkflowFileLink } from '@/types/graph';
import { namespace, Mutation } from 'vuex-class';
import { deepJSONCopy } from '@/lib/general-utils';
import { CodeBlockSharedFilesPaneModule } from '@/store/modules/panes/code-block-shared-files';
import { languageToFileExtension } from '@/utils/project-debug-utils';
import ViewSharedFileLinkPane, {
  ViewSharedFileLinkProps
} from '@/components/ProjectEditor/shared-files-components/ViewSharedFilesList';
import { getSharedFilesForCodeBlock } from '@/utils/project-helpers';
import { AddSharedFileLinkArguments, FileNodeMetadata, FileNodeMetadataTypes } from '@/types/shared-files';

import SlVueTree, { ISlTreeNodeModel } from 'sl-vue-tree';
import 'sl-vue-tree/dist/sl-vue-tree-dark.css';

const project = namespace('project');

@Component({
  components: {
    SlVueTree
  }
})
export default class CodeBlockSharedFilesPane extends Vue {
  treeViewInstance!: SlVueTree<FileNodeMetadata>;

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

  getFileNodeFromSharedFileId(sharedFileLink: WorkflowFileLink): ISlTreeNodeModel<FileNodeMetadata> | null {
    const sharedFile = this.getSharedFileById(sharedFileLink.file_id);

    if (sharedFile === null) {
      return null;
    }

    return {
      title: sharedFile.name,
      isLeaf: true,
      isDraggable: false,
      data: {
        id: sharedFileLink.file_id,
        type: FileNodeMetadataTypes.sharedFileLink
      }
    };
  }

  getBlockFileSystemTree(): ISlTreeNodeModel<FileNodeMetadata>[] {
    const sharedLinks = this.getSharedLinksForCodeBlock();

    const rawFileNodes = sharedLinks.map(sharedFileLink => this.getFileNodeFromSharedFileId(sharedFileLink));

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

  selectedFolder(event: any) {
    const fileNodeMetadata = event.data as FileNodeMetadata | null;

    if (fileNodeMetadata === null) {
      return;
    }

    // If it's the lambda.EXT then we open the Code Block
    if (fileNodeMetadata.type === FileNodeMetadataTypes.codeBlock) {
      this.selectNode(fileNodeMetadata.id);
    }

    // Must be a shared file
    if (fileNodeMetadata.type !== FileNodeMetadataTypes.sharedFileLink) {
      return;
    }

    // Get shared file
    const sharedFile = this.getSharedFileById(fileNodeMetadata.id);

    // If it's null, drop out.
    if (sharedFile === null) {
      return;
    }

    // Set the shared file.
    EditSharedFilePaneModule.openSharedFile(sharedFile);
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

  getCurrentlyViewingCodeBlock() {
    return (
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
    );
  }

  getCodeBlockSharedFilesPane() {
    if (this.openedProject === null || CodeBlockSharedFilesPaneModule.codeBlock === null) {
      return <div>No project is opened!</div>;
    }

    const treeProps = {
      value: this.getBlockFileSystemTree()
    };

    const sharedFiles = getSharedFilesForCodeBlock(CodeBlockSharedFilesPaneModule.codeBlock.id, this.openedProject);

    const viewSharedFileLinkPaneProps: ViewSharedFileLinkProps = {
      sharedFileClickHandler: CodeBlockSharedFilesPaneModule.addSharedFileToCodeBlock,
      sharedFilesText: 'All Shared Files (click to add to Code Block): ',
      sharedFilesArray: sharedFiles
    };
    return (
      <div>
        <b-form-group description="This is a file view of this Code Block's Shared Files. All shared files are placed in the shared_files directory.">
          <div class="display--flex flex-wrap mb-1">
            <label class="d-block flex-grow--1 pt-1">Code Block's Files (click a file to open it):</label>
          </div>
          {/*
          // @ts-ignore*/}
          <SlVueTree props={treeProps} on={{ nodeclick: this.selectedFolder }} ref="treeView" />
        </b-form-group>

        <h4>Add Shared File to Code Block</h4>
        <ViewSharedFileLinkPane props={viewSharedFileLinkPaneProps} />
      </div>
    );
  }

  mounted() {
    if (!this.$refs.treeView) {
      throw new Error('Could not load tree view for component');
    }

    this.treeViewInstance = this.$refs.treeView as SlVueTree<FileNodeMetadata>;
  }

  public render(h: CreateElement): VNode {
    return (
      <div class="text-align--left ml-2 mr-2 mt-0 display--flex flex-direction--column shared-file-links-pane">
        {this.getCurrentlyViewingCodeBlock()}

        {this.getCodeBlockSharedFilesPane()}
      </div>
    );
  }
}

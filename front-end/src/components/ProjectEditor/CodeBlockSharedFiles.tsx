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
  @project.State openedProject!: RefineryProject | null;

  selectedFileTreeNode(event: any) {
    const fileNodeMetadata = event.data as FileNodeMetadata | null;

    if (!fileNodeMetadata) {
      return;
    }

    CodeBlockSharedFilesPaneModule.selectedFileTreeNode(fileNodeMetadata);
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
      value: CodeBlockSharedFilesPaneModule.blockFileSystemTree
    };

    const viewSharedFileLinkPaneProps: ViewSharedFileLinkProps = {
      sharedFileClickHandler: CodeBlockSharedFilesPaneModule.addSharedFileToCodeBlock,
      sharedFilesText: 'All Shared Files Not Already In Code Block (click to add to Code Block): ',
      sharedFilesArray: CodeBlockSharedFilesPaneModule.sharedFilesNotAlreadyInCodeBlock
    };
    return (
      <div>
        <b-form-group description="This is a file view of this Code Block's Shared Files. All shared files are placed in the shared_files directory.">
          <div class="display--flex flex-wrap mb-1">
            <label class="d-block flex-grow--1 pt-1">Code Block's Files (click a file to open it):</label>
          </div>
          {/*
          // @ts-ignore*/}
          <SlVueTree props={treeProps} on={{ nodeclick: this.selectedFileTreeNode }} ref="treeView" />
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

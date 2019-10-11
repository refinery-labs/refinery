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
import { namespace } from 'vuex-class';
import { deepJSONCopy } from '@/lib/general-utils';

const project = namespace('project');

@Component
export default class EditSharedFileLinksPane extends Vue {
  @project.State openedProject!: RefineryProject | null;
  @project.Action selectNode!: (nodeId: string) => void;
  @project.Action deleteSharedFileLink!: (sharedFileLink: WorkflowFileLink) => void;

  getNodeByID(nodeID: string) {
    if (this.openedProject === null) {
      return null;
    }

    const matchingNodes = this.openedProject.workflow_states.filter(workflow_state => {
      return workflow_state.id === nodeID;
    });

    return matchingNodes[0];
  }

  getSharedLinksForSharedFile(sharedFileID: string) {
    if (this.openedProject === null) {
      return [];
    }

    return this.openedProject.workflow_file_links.filter(
      workflow_file_link => workflow_file_link.file_id === sharedFileID
    );
  }

  selectCodeBlock(nodeId: string) {
    this.selectNode(nodeId);
  }

  public renderSharedFileLinkSelect(codeBlock: LambdaWorkflowState, sharedFileLink: WorkflowFileLink) {
    if (EditSharedFilePaneModule.sharedFile === null) {
      return <i>No Shared File is selected!</i>;
    }

    return (
      <b-list-group-item class="display--flex">
        <img class="add-block__image" src={require('../../../public/img/node-icons/code-icon.png')} />
        <div class="flex-column align-items-start add-block__content">
          <div class="d-flex w-100 justify-content-between">
            <h4 class="mb-1">{codeBlock.name}</h4>
          </div>

          <p class="mb-1">
            Block language is <code>{codeBlock.language}</code>, and the Shared File is located at{' '}
            <code>{'./shared_files/' + sharedFileLink.path + EditSharedFilePaneModule.sharedFile.name}</code>.
          </p>
          <div class="container">
            <div class="row">
              <b-button on={{ click: () => this.selectCodeBlock(codeBlock.id) }} variant="primary" class="mt-2 mr-1">
                Select Block
              </b-button>
              <b-button
                on={{ click: () => EditSharedFilePaneModule.viewCodeBlockSharedFiles(codeBlock) }}
                variant="primary"
                class="mt-2 mr-1"
              >
                View Block Shared Files
              </b-button>
              <b-button
                on={{ click: () => this.deleteSharedFileLink(sharedFileLink) }}
                variant="danger"
                class="mt-2 mr-1"
              >
                Unlink from Block
              </b-button>
            </div>
          </div>
        </div>
      </b-list-group-item>
    );
  }

  public getSharedFileLinks() {
    if (EditSharedFilePaneModule.sharedFile === null) {
      return [];
    }

    const sharedLinks = this.getSharedLinksForSharedFile(EditSharedFilePaneModule.sharedFile.id);

    if (sharedLinks.length === 0) {
      return (
        <div class="text-align--center mb-3 mt-3">
          <i>
            This Shared File has not been added to any Code Blocks. <br /> Click the button below to add it to one.
          </i>
        </div>
      );
    }

    return sharedLinks.map(workflow_file_link => {
      return this.renderSharedFileLinkSelect(
        this.getNodeByID(workflow_file_link.node) as LambdaWorkflowState,
        workflow_file_link
      );
    });
  }

  public getSharedFileLinksTitleText() {
    if (EditSharedFilePaneModule.sharedFile === null) {
      return <h3>No shared file is selected!</h3>;
    }

    return (
      <div class="text-align--center">
        <h3>
          <code>{EditSharedFilePaneModule.sharedFile.name}</code> is in the following Code Block(s):
        </h3>
      </div>
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <div class="text-align--left mb-2 ml-2 mr-2 mt-0 display--flex flex-direction--column shared-file-links-pane">
        <b-form-group>
          <a
            href=""
            class="mt-2 d-block"
            on={{ click: preventDefaultWrapper(EditSharedFilePaneModule.navigateToPreviousSharedFilesPane) }}
          >
            {'<< Go Back'}
          </a>
        </b-form-group>

        {this.getSharedFileLinksTitleText()}

        <div class="flex-grow--1 scrollable-pane-container shared-file-links-well">
          <b-list-group className="shared-file-link-container">{this.getSharedFileLinks()}</b-list-group>
        </div>

        <div class="container">
          <div class="row">
            <b-button
              on={{ click: () => EditSharedFilePaneModule.selectCodeBlockToAddSharedFileTo() }}
              variant="primary"
              class="w-100 mt-2"
            >
              Add Shared File to Block
            </b-button>
          </div>
        </div>
      </div>
    );
  }
}

import Component from 'vue-class-component';
import Vue, { CreateElement, VNode } from 'vue';
import { RefineryProject, WorkflowFile } from '@/types/graph';
import { namespace } from 'vuex-class';
import { Prop } from 'vue-property-decorator';
import { SharedFilesPaneModule } from '@/store';

const project = namespace('project');

export interface ViewSharedFileLinkProps {
  sharedFilesArray: WorkflowFile[];
  sharedFileClickHandler: (workflowFile: WorkflowFile) => void;
  sharedFilesText: string;
}

@Component
export default class ViewSharedFileLinkPane extends Vue {
  @Prop({ required: true }) sharedFilesArray!: WorkflowFile[];
  @Prop({ required: true }) sharedFileClickHandler!: (workflowFile: WorkflowFile) => void;
  @Prop({ required: true }) sharedFilesText!: string;

  async openSharedFileInEditor(sharedFile: WorkflowFile) {
    await this.sharedFileClickHandler(sharedFile);
  }

  getSharedFiles() {
    return this.sharedFilesArray.filter(workflow_file => {
      return workflow_file.name.toLowerCase().includes(SharedFilesPaneModule.searchText.toLowerCase());
    });
  }

  public renderBlockSelect(workflowFile: WorkflowFile) {
    return (
      <b-list-group-item class="display--flex" button on={{ click: () => this.openSharedFileInEditor(workflowFile) }}>
        <code>{workflowFile.name}</code>
      </b-list-group-item>
    );
  }

  public renderExistingSharedFiles() {
    const sharedFiles = this.getSharedFiles();

    if (sharedFiles.length === 0) {
      return (
        <div class="flex-grow--1 padding-left--micro padding-right--micro text-align--center mt-2 mb-2 ml-2 mr-2">
          <i>No Shared Files found.</i>
        </div>
      );
    }

    return (
      <div class="flex-grow--1 padding-left--micro padding-right--micro">
        <b-list-group class="add-saved-block-container add-block-container">
          {sharedFiles.map(result => this.renderBlockSelect(result))}
        </b-list-group>
      </div>
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <div>
        <label class="d-block">{this.sharedFilesText}</label>
        <div class="flex-grow--1 scrollable-pane-container shared-files-well">{this.renderExistingSharedFiles()}</div>
        <b-form-input
          type="search"
          autofocus={false}
          required={false}
          value={SharedFilesPaneModule.searchText}
          on={{ input: SharedFilesPaneModule.setSearchText }}
          placeholder="Search shared files here..."
          class="mt-2"
        />
        <small class="form-text text-muted">
          Enter text to search through all existing Shared Files for this project.
        </small>
      </div>
    );
  }
}

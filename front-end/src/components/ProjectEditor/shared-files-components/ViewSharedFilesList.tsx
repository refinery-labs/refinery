import Component from 'vue-class-component';
import Vue, { CreateElement, VNode } from 'vue';
import { EditSharedFilePaneModule } from '@/store/modules/panes/edit-shared-file';
import { EditSharedFileLinksPaneModule } from '@/store/modules/panes/edit-shared-file-links';
import { SharedFilesPaneModule } from '@/store/modules/panes/shared-files';
import { RefineryProject, WorkflowFile } from '@/types/graph';
import { namespace } from 'vuex-class';
import { Prop } from 'vue-property-decorator';

const project = namespace('project');

export interface ViewSharedFileLinkProps {}

@Component
export default class ViewSharedFileLinkPane extends Vue {
  @project.State openedProject!: RefineryProject | null;
  @Prop({ required: true }) sharedFileClickHandler!: (workflowFile: WorkflowFile) => void;
  @Prop({ required: true }) sharedFilesText!: string;

  async openSharedFileInEditor(sharedFile: WorkflowFile) {
    await this.sharedFileClickHandler(sharedFile);
  }

  getSharedFiles() {
    if (this.openedProject === null) {
      return [];
    }
    return this.openedProject.workflow_files.filter(workflow_file => {
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
          <i>There are currently no Shared Files, you can add one by using the form below.</i>
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
        <b-form-group>
          <div class="flex-grow--1 scrollable-pane-container shared-files-well">{this.renderExistingSharedFiles()}</div>
          <b-form-input
            type="search"
            autofocus={true}
            required={true}
            value={SharedFilesPaneModule.searchText}
            on={{ input: SharedFilesPaneModule.setSearchText }}
            placeholder="Search shared files here..."
            class="mt-2"
          />
          <small class="form-text text-muted">
            Enter text to search through all existing Shared Files for this project.
          </small>
        </b-form-group>
      </div>
    );
  }
}

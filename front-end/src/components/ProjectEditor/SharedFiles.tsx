import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { RefineryProject, WorkflowFile } from '@/types/graph';
import { AddSharedFileArguments } from '@/store/modules/project-view';
import { SharedFilesPaneModule } from '@/store/modules/panes/shared-files';
import { EditSharedFilePaneModule } from '@/store/modules/panes/edit-shared-file';
import { ProjectViewActions } from '@/constants/store-constants';
import { deepJSONCopy } from '@/lib/general-utils';
import store from '@/store/index';

const project = namespace('project');

@Component
export default class SharedFilesPane extends Vue {
  @project.State openedProject!: RefineryProject | null;
  @project.Action addSharedFile!: (addSharedFileArgs: AddSharedFileArguments) => WorkflowFile;

  async addNewSharedFile() {
    const addSharedFileArgs: AddSharedFileArguments = {
      name: SharedFilesPaneModule.addSharedFileName,
      body: ''
    };
    const newSharedFile = await this.addSharedFile(addSharedFileArgs);
    await EditSharedFilePaneModule.openSharedFile(newSharedFile);
    SharedFilesPaneModule.resetState();
  }

  async openSharedFileInEditor(sharedFile: WorkflowFile) {
    await EditSharedFilePaneModule.openSharedFile(sharedFile);
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
        {workflowFile.name}
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
      <div class="text-align--left mb-2 ml-2 mr-2 mt-0 display--flex flex-direction--column shared-files-pane">
        <b-form-group
          className="padding-bottom--normal-small margin-bottom--normal-small"
          description="Specify some text to search the existing Shared Files for this project."
        >
          <div class="display--flex">
            <label class="flex-grow--1">Search by Name:</label>
          </div>
          <b-form-input
            type="text"
            autofocus={true}
            required={true}
            value={SharedFilesPaneModule.searchText}
            on={{ input: SharedFilesPaneModule.setSearchText }}
            placeholder="eg, utils.py"
          />
        </b-form-group>

        <label class="d-block">Existing Shared Files: </label>
        <b-form-group>
          <div class="flex-grow--1 scrollable-pane-container shared-files-well">{this.renderExistingSharedFiles()}</div>
        </b-form-group>

        <b-list-group>
          <b-form-group
            className="padding-bottom--normal-small margin-bottom--normal-small"
            description="Name of the new shared file to create."
          >
            <label class="d-block">New Shared File Name:</label>
            <b-form-input
              type="text"
              autofocus={true}
              required={true}
              value={SharedFilesPaneModule.addSharedFileName}
              on={{ input: SharedFilesPaneModule.setSharedFileName }}
              state={SharedFilesPaneModule.newSharedFilenameIsValid}
              placeholder="ex, utils.py"
            />
            <b-form-invalid-feedback state={SharedFilesPaneModule.newSharedFilenameIsValid}>
              That is not a valid file name.
            </b-form-invalid-feedback>
          </b-form-group>
          <b-button
            on={{ click: () => this.addNewSharedFile() }}
            disabled={!SharedFilesPaneModule.newSharedFilenameIsValid}
            variant="primary"
          >
            Create new shared file
          </b-button>
        </b-list-group>
      </div>
    );
  }
}
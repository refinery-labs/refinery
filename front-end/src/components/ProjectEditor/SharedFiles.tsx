import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { RefineryProject, WorkflowFile } from '@/types/graph';
import ViewSharedFileLinkPane, {
  ViewSharedFileLinkProps
} from '@/components/ProjectEditor/shared-files-components/ViewSharedFilesList';
import { AddSharedFileArguments } from '@/types/shared-files';
import { EditSharedFilePaneModule, SharedFilesPaneModule } from '@/store';

const project = namespace('project');

@Component
export default class SharedFilesPane extends Vue {
  @project.State openedProject!: RefineryProject | null;
  @project.Action addSharedFile!: (addSharedFileArgs: AddSharedFileArguments) => WorkflowFile;

  public render(h: CreateElement): VNode {
    if (this.openedProject === null) {
      return <div>No project is opened!</div>;
    }

    const viewSharedFileLinkPaneProps: ViewSharedFileLinkProps = {
      sharedFileClickHandler: EditSharedFilePaneModule.openSharedFile,
      sharedFilesText: 'All Shared Files (click to open): ',
      sharedFilesArray: this.openedProject.workflow_files
    };

    const containerClasses = {
      'shared-files-pane': true,
      // formatting
      'text-align--left display--flex flex-direction--column': true,
      // margins
      'mb-2 ml-2 mr-2 mt-0': true
    };

    return (
      <div class={containerClasses}>
        <b-list-group class="mb-4">
          <h4>Create New Shared File</h4>
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
          <small class="form-text text-muted">Name of the new shared file to create.</small>
          <b-form-invalid-feedback state={SharedFilesPaneModule.newSharedFilenameIsValid}>
            That is not a valid file name.
          </b-form-invalid-feedback>
          <b-button
            on={{ click: () => SharedFilesPaneModule.addNewSharedFile() }}
            disabled={!SharedFilesPaneModule.newSharedFilenameIsValid}
            variant="primary"
            class="mt-2"
          >
            Create new shared file
          </b-button>
        </b-list-group>

        <h4>Open Existing Shared File</h4>
        <ViewSharedFileLinkPane props={viewSharedFileLinkPaneProps} />
      </div>
    );
  }
}

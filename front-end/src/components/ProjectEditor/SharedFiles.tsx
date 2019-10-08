import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { RefineryProject, WorkflowFile } from '@/types/graph';
import { AddSharedFileArguments } from '@/store/modules/project-view';
import { SharedFilesPaneModule } from '@/store/modules/panes/shared-files';
import { EditSharedFilePaneModule } from '@/store/modules/panes/edit-shared-file';
import ViewSharedFileLinkPane, {
  ViewSharedFileLinkProps
} from '@/components/ProjectEditor/shared-files-components/ViewSharedFilesList';

const project = namespace('project');

@Component
export default class SharedFilesPane extends Vue {
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

  public render(h: CreateElement): VNode {
    const viewSharedFileLinkPaneProps: ViewSharedFileLinkProps = {
      sharedFileClickHandler: EditSharedFilePaneModule.openSharedFile,
      sharedFilesText: 'All Shared Files (click to open): '
    };

    return (
      <div class="text-align--left mb-2 ml-2 mr-2 mt-0 display--flex flex-direction--column shared-files-pane">
        <ViewSharedFileLinkPane props={viewSharedFileLinkPaneProps} />
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

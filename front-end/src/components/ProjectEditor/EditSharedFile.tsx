import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { EditorProps } from '@/types/component-types';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import { BlockDocumentationButton } from '@/components/ProjectEditor/block-components/EditBlockDocumentationButton';
import { SupportedLanguage, WorkflowFile } from '@/types/graph';
import { EditSharedFilePaneModule } from '@/store/modules/panes/edit-shared-file';
import { languageToFileExtension } from '@/utils/project-debug-utils';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import { SharedFilesPaneModule } from '@/store/modules/panes/shared-files';

const project = namespace('project');

@Component
export default class EditSharedFilePane extends Vue {
  @project.Action saveSharedFile!: (savedFile: WorkflowFile) => void;

  public renderCodeEditor(extraClasses?: string, disableFullscreen?: boolean) {
    if (EditSharedFilePaneModule.sharedFile === null) {
      return 'No file is opened!';
    }

    const editorProps: EditorProps = {
      name: `shared-file-editor-REPLACEME`,
      lang: EditSharedFilePaneModule.getFileLanguage,
      readOnly: false,
      content: EditSharedFilePaneModule.sharedFile ? EditSharedFilePaneModule.sharedFile.body : '',
      // Update below to set state
      onChange: EditSharedFilePaneModule.codeEditorChange,
      disableFullscreen: false
    };

    return <RefineryCodeEditor props={editorProps} />;
  }

  public renderCodeEditorContainer() {
    return (
      <b-form-group
        id={`shared-file-editor-group`}
        description="This editor allows you to modify the contents of this shared file. You can then link this file to your Code Blocks to share libraries across deployed blocks."
      >
        <div class="display--flex flex-wrap">
          <label class="d-block flex-grow--1 pt-2" htmlFor={`code-editor-REPLACEME`}>
            Edit Shared File:
          </label>
          <div class="flex-grow display--flex mb-1">
            <BlockDocumentationButton
              props={{ docLink: 'https://docs.refinery.io/blocks/#code-block', offsetButton: false }}
            />
          </div>
        </div>
        <div class="input-group with-focus shared-file-editor">{this.renderCodeEditor()}</div>
      </b-form-group>
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <div class="text-align--left mb-2 ml-2 mr-2 mt-0 display--flex flex-direction--column shared-files-pane">
        <a
          href=""
          class="mb-2 padding-bottom--normal mt-2 d-block"
          style="border-bottom: 1px dashed #eee;"
          on={{ click: preventDefaultWrapper(EditSharedFilePaneModule.navigateToPreviousSharedFilesPane) }}
        >
          {'<< Go Back'}
        </a>
        <b-form-group
          className="padding-bottom--normal-small margin-bottom--normal-small"
          description="Name of the new shared file to create."
        >
          <label class="d-block">Shared File Name:</label>
          <b-form-input
            type="text"
            autofocus={true}
            required={true}
            value={EditSharedFilePaneModule.sharedFile ? EditSharedFilePaneModule.sharedFile.name : ''}
            on={{ input: EditSharedFilePaneModule.fileNameChange }}
            state={EditSharedFilePaneModule.newSharedFilenameIsValid}
            placeholder="ex, utils.py"
          />
          <b-form-invalid-feedback state={EditSharedFilePaneModule.newSharedFilenameIsValid}>
            That is not a valid file name.
          </b-form-invalid-feedback>
        </b-form-group>

        {this.renderCodeEditorContainer()}

        <div class="container">
          <div class="row">
            <div class="col-sm pr-1 pl-0">
              <b-button
                on={{ click: () => EditSharedFilePaneModule.openSharedFileLinks() }}
                variant="primary"
                class="w-100"
              >
                Edit Shared File Links
              </b-button>
            </div>
            <div class="col-sm pr-0 pl-0">
              <b-button
                on={{ click: () => EditSharedFilePaneModule.selectCodeBlockToAddSharedFileTo() }}
                variant="primary"
                className="w-100"
              >
                Add Shared File to Block
              </b-button>
            </div>
            <div class="col-sm pr-0 pl-0">
              <b-button
                on={{ click: () => EditSharedFilePaneModule.deleteSharedFile() }}
                variant="danger"
                class="w-100"
              >
                Delete Shared File
              </b-button>
            </div>
          </div>
        </div>
      </div>
    );
  }
}

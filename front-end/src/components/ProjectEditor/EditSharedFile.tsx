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

const project = namespace('project');

@Component
export default class EditSharedFilePane extends Vue {
  @project.Action saveSharedFile!: (savedFile: WorkflowFile) => void;

  codeEditorChange(value: string) {
    EditSharedFilePaneModule.setSharedFileBody(value);
    EditSharedFilePaneModule.saveSharedFile();
  }

  getLanguageFromFileExtension(fileExtension: string): SupportedLanguage {
    // This is gross, I would've thought their would be a Rambda function for this... (getting key from value in object)
    const matchingExtensions = Object.entries(languageToFileExtension).filter(extensionPair => {
      return fileExtension.replace('.', '') === extensionPair[1];
    });

    if (matchingExtensions.length > 0) {
      return matchingExtensions[0][0] as SupportedLanguage;
    }

    return SupportedLanguage.NODEJS_10;
  }

  getLanguageFromFileName(fileName: string): SupportedLanguage {
    const languageFileExtensions = Object.values(languageToFileExtension).map(extension => {
      return '.' + extension;
    });

    const matchingFileExtensions = languageFileExtensions.filter(fileExtension => {
      return fileName.toLowerCase().endsWith(fileExtension);
    });

    if (matchingFileExtensions.length > 0) {
      return this.getLanguageFromFileExtension(matchingFileExtensions[0]);
    }

    return SupportedLanguage.NODEJS_10;
  }

  public renderCodeEditor(extraClasses?: string, disableFullscreen?: boolean) {
    if (EditSharedFilePaneModule.sharedFile === null) {
      return 'No file is opened!';
    }

    const editorLanguage = this.getLanguageFromFileName(EditSharedFilePaneModule.sharedFile.name);

    const editorProps: EditorProps = {
      name: `shared-file-editor-REPLACEME`,
      lang: editorLanguage,
      readOnly: false,
      content: EditSharedFilePaneModule.sharedFile ? EditSharedFilePaneModule.sharedFile.body : '',
      // Update below to set state
      onChange: this.codeEditorChange,
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

  fileNameChanged(fileName: string) {
    if (fileName === undefined) {
      return;
    }
    EditSharedFilePaneModule.setSharedFileName(fileName);
    EditSharedFilePaneModule.saveSharedFile();
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
            on={{ input: this.fileNameChanged }}
            //state={SharedFilesPaneModule.newSharedFilenameIsValid}
            placeholder="ex, utils.py"
          />
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

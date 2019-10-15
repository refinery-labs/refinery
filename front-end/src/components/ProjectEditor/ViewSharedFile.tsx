import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { EditorProps } from '@/types/component-types';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import { SupportedLanguage } from '@/types/graph';
import { ViewSharedFilePaneModule } from '@/store';
import { preventDefaultWrapper } from '@/utils/dom-utils';

const project = namespace('project');

@Component
export default class ViewSharedFilePane extends Vue {
  public renderCodeEditor(extraClasses?: string, disableFullscreen?: boolean) {
    const editorProps: EditorProps = {
      name: `View Shared File`,
      lang: ViewSharedFilePaneModule.getFileLanguage,
      readOnly: false,
      content: ViewSharedFilePaneModule.sharedFile ? ViewSharedFilePaneModule.sharedFile.body : '',
      disableFullscreen: false
    };

    return <RefineryCodeEditor props={editorProps} />;
  }

  public renderCodeEditorContainer() {
    return (
      <b-form-group
        id={`shared-file-editor-group`}
        description="This is a shared file from the saved block, if you add this block to your project the shared files will be added as well."
        class="mb-0 pb-2"
      >
        <div class="input-group with-focus shared-file-editor">{this.renderCodeEditor()}</div>
      </b-form-group>
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <div class="view-shared-file-pane text-align--left">
        <a
          href=""
          class="mb-2 padding-bottom--normal mt-2 ml-2 d-block"
          style="border-bottom: 1px dashed #eee;"
          on={{ click: preventDefaultWrapper(ViewSharedFilePaneModule.backToSavedBlockView) }}
        >
          {'<< Go Back'}
        </a>
        <div class="text-align--left mb-0 ml-2 mr-2 mt-0 pb-0 display--flex flex-direction--column">
          <h2>
            Saved Block Shared File:{' '}
            <code>{ViewSharedFilePaneModule.sharedFile ? ViewSharedFilePaneModule.sharedFile.name : ''}</code>
          </h2>
          {this.renderCodeEditorContainer()}
        </div>
      </div>
    );
  }
}

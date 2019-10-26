import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { EditorProps, MarkdownProps } from '@/types/component-types';
import { RefineryProject } from '@/types/graph';
import RefineryMarkdown from '@/components/Common/RefineryMarkdown';
import { ReadmeEditorPaneStoreModule } from '@/store';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import Split from '@/components/Common/Split.vue';
import SplitArea from '@/components/Common/SplitArea.vue';

const project = namespace('project');

@Component
export default class EditReadmePane extends Vue {
  @project.State openedProject!: RefineryProject | null;

  public renderMarkdownEditorModal() {
    if (!this.openedProject) {
      return <span>Please open project!</span>;
    }

    const editorProps: EditorProps = {
      name: `README Editor`,
      lang: 'markdown',
      content: this.openedProject.readme,
      readOnly: false,
      onChange: ReadmeEditorPaneStoreModule.setReadmeContents
    };

    const modalOnHandlers = {
      hidden: () => {
        ReadmeEditorPaneStoreModule.setFullScreenEditorModalVisibilityAction(false);
      }
    };

    const markdownProps: MarkdownProps = {
      content: this.openedProject.readme
    };

    return (
      <b-modal
        ref={`readme-editor--fullscreen-modal`}
        on={modalOnHandlers}
        hide-footer={true}
        no-close-on-esc={true}
        size="xl no-max-width no-modal-body-padding dark-modal"
        title={`README Editor`}
        visible={ReadmeEditorPaneStoreModule.isFullScreenEditorModalVisible}
      >
        <div class="display--flex code-modal-editor-container overflow--hidden-x">
          <Split
            props={{
              direction: 'horizontal' as Object,
              extraClasses: 'height--100percent flex-grow--1 display--flex' as Object
            }}
          >
            <SplitArea props={{ size: 67 as Object, positionRelative: true as Object }}>
              <RefineryCodeEditor props={editorProps} />
            </SplitArea>
            <SplitArea
              props={{
                size: 33 as Object,
                extraClasses: 'container markdown-view-fullscreen-modal pl-3 pr-3 pt-3' as Object
              }}
            >
              <RefineryMarkdown props={markdownProps} />
            </SplitArea>
          </Split>
        </div>
      </b-modal>
    );
  }

  public render(h: CreateElement): VNode {
    if (!this.openedProject) {
      return <span>Please open project!</span>;
    }

    const editorProps: EditorProps = {
      name: `README Editor`,
      lang: 'markdown',
      content: this.openedProject.readme,
      readOnly: false,
      onChange: ReadmeEditorPaneStoreModule.setReadmeContents,
      fullscreenToggled: () => {
        ReadmeEditorPaneStoreModule.setFullScreenEditorModalVisibilityAction(true);
      }
    };

    const markdownProps: MarkdownProps = {
      content: this.openedProject.readme
    };

    return (
      <div class="markdown-editor-pane display--flex flex-direction--column height--100percent text-align--left">
        <div style="flex: 1; min-height: 40%;">
          <RefineryCodeEditor props={editorProps} />
        </div>
        <div class="mt-3 mb-3 ml-3 mr-3" style="flex: 1;">
          <RefineryMarkdown props={markdownProps} />
          {this.renderMarkdownEditorModal()}
        </div>
      </div>
    );
  }
}

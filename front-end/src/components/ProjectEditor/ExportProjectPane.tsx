import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { RefineryProject, SupportedLanguage } from '@/types/graph';
import { languageToAceLangMap, PANE_POSITION } from '@/types/project-editor-types';
import { EditorProps } from '@/types/component-types';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';

const project = namespace('project');

@Component
export default class ExportProjectPane extends Vue {
  @project.State openedProject!: RefineryProject | null;

  @project.Getter exportProjectJson!: string;

  @project.Action closePane!: (p: PANE_POSITION) => void;

  public renderCodeEditor() {
    if (!this.openedProject) {
      return <span>Please open project!</span>;
    }

    const editorProps: EditorProps = {
      name: `editor-export-project`,
      // Set Nodejs because it supports JSON
      lang: SupportedLanguage.NODEJS_8,
      content: this.exportProjectJson
    };

    return <RefineryCodeEditor props={editorProps} />;
  }

  public render(h: CreateElement): VNode {
    if (!this.openedProject) {
      return <span>Please open project!</span>;
    }

    const formClasses = {
      'mb-2 mt-2 export-project-container': true
    };

    return (
      <div class={formClasses}>
        <div class="export-project-container__content overflow--scroll-y-auto display--flex text-align--left">
          {this.renderCodeEditor()}
        </div>
        <div class="ml-2 mr-2 mt-2 justify-content-center">
          <b-button-group class="col-12 mr-0 ml-0 padding--none">
            <b-button
              variant="primary"
              class="col-12 mr-0 ml-0"
              target="_blank"
              href={`data:text/json;charset=utf-8,${encodeURIComponent(this.exportProjectJson)}`}
              download={`${this.openedProject.name
                .toLowerCase()
                .split(' ')
                .join('-')}.json`}
            >
              Download as JSON
            </b-button>
          </b-button-group>
        </div>
      </div>
    );
  }
}

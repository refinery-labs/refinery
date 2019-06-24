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
    const formClasses = {
      'mb-3 mt-3 text-align--left export-project-container': true
    };

    return (
      <div class={formClasses}>
        <div class="export-project-container__content overflow--scroll-y-auto display--flex">
          {this.renderCodeEditor()}
        </div>
        <div class="row export-project-container__bottom-buttons">
          <b-button-group class="col-12">
            {/*This is hacky to make this close itself but meh we can fix it later*/}
            <b-button variant="secondary" class="col-12" on={{ click: () => this.closePane(PANE_POSITION.left) }}>
              Close
            </b-button>
          </b-button-group>
        </div>
      </div>
    );
  }
}

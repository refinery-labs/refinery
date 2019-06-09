import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import {RefineryProject, SupportedLanguage} from '@/types/graph';
import AceEditor from '@/components/Common/AceEditor.vue';
import {languageToAceLangMap, PANE_POSITION} from '@/types/project-editor-types';

const project = namespace('project');

@Component
export default class ExportProjectPane extends Vue {
  @project.State openedProject!: RefineryProject | null;

  @project.Action closePane!: (p: PANE_POSITION) => void;


  public renderCodeEditor() {
    if (!this.openedProject) {
      return (
        <span>Please open project!</span>
      );
    }

    const editorProps = {
      'editor-id': `editor-export-project-${this.openedProject.project_id}`,
      // Set Nodejs because it supports JSON
      lang: languageToAceLangMap[SupportedLanguage.NODEJS_8],
      theme: 'monokai',
      content: JSON.stringify(this.openedProject, null, '  ')
    };

    return (
      // @ts-ignore
      <AceEditor
        editor-id={editorProps['editor-id']}
        lang={editorProps.lang}
        theme="monokai"
        content={editorProps.content}
      />
    );
  }

  public render(h: CreateElement): VNode {

    const formClasses = {
      'mb-3 mt-3 text-align--left export-project-container': true
    };

    return (
      <div class={formClasses}>
        <div class="export-project-container__content overflow--scroll-y-auto">
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

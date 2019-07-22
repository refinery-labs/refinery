import copy from 'copy-to-clipboard';
import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { RefineryProject, SupportedLanguage } from '@/types/graph';
import { PANE_POSITION } from '@/types/project-editor-types';
import { EditorProps } from '@/types/component-types';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';

const project = namespace('project');

@Component
export default class ExportProjectPane extends Vue {
  copyLinkOverride: string | null = null;

  @project.State openedProject!: RefineryProject | null;

  @project.Getter exportProjectJson!: string;
  @project.Getter shareProjectUrl!: string;

  @project.Action closePane!: (p: PANE_POSITION) => void;

  copyLink() {
    copy(this.shareProjectUrl);

    this.copyLinkOverride = 'Link Copied!';
    setTimeout(() => (this.copyLinkOverride = null), 1000);
  }

  public renderExportJson() {
    if (!this.openedProject) {
      return <span>Please open project!</span>;
    }

    const editorProps: EditorProps = {
      name: `editor-export-project`,
      lang: 'json',
      content: this.exportProjectJson
    };

    return <RefineryCodeEditor props={editorProps} />;
  }

  public renderShareJson() {
    if (!this.openedProject) {
      return <span>Please open project!</span>;
    }

    return (
      <div class="padding-left--normal padding-right--normal mt-2">
        <div class="text-align--left run-lambda-container__text-label">
          <label class="text-light padding--none mt-0 mb-0 ml-2">Share Link:</label>
        </div>
        <b-form-textarea style="height: 40px; min-width: 300px" value={this.shareProjectUrl} />
        <b-button variant="primary" class="col-12 mt-2 mb-2" on={{ click: this.copyLink }}>
          {this.copyLinkOverride || (
            <span>
              <i class="far fa-copy" /> Copy Link to Clipboard
            </span>
          )}
        </b-button>
      </div>
    );
  }

  public render(h: CreateElement): VNode {
    if (!this.openedProject) {
      return <span>Please open project!</span>;
    }

    const formClasses = {
      'export-project-container': true
    };

    return (
      <div class={formClasses}>
        <b-tabs nav-class="nav-justified" content-class="padding--none">
          <b-tab title="first" active>
            <template slot="title">Share Project</template>
            {this.renderShareJson()}
          </b-tab>
          <b-tab>
            <template slot="title">Share Project</template>
            <div class="export-project-container__content overflow--scroll-y-auto flex-direction--column display--flex text-align--left">
              <div class="text-align--left run-lambda-container__text-label">
                <label class="text-light padding--none mt-0 mb-0 ml-2">Exported Project JSON:</label>
              </div>
              {this.renderExportJson()}
            </div>
            <div class="m-2 justify-content-center">
              <b-button
                variant="primary"
                class="col-12 ml-0 mr-0"
                target="_blank"
                href={`data:text/json;charset=utf-8,${encodeURIComponent(this.exportProjectJson)}`}
                download={`${this.openedProject.name
                  .toLowerCase()
                  .split(' ')
                  .join('-')}.json`}
              >
                Download as JSON
              </b-button>
            </div>
          </b-tab>
        </b-tabs>
      </div>
    );
  }
}

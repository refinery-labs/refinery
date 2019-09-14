import { CreateElement, VNode } from 'vue';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { EditorProps } from '@/types/component-types';
import { SupportedLanguage } from '@/types/graph';
import { languageToAceLangMap } from '@/types/project-editor-types';
import MonacoEditor, { MonacoEditorProps } from '@/lib/MonacoEditor';

@Component
export default class RefineryCodeEditor extends Vue implements EditorProps {
  fullscreen = false;

  @Prop({ required: true }) name!: string;
  @Prop({ required: true }) lang!: SupportedLanguage | 'text' | 'json';
  @Prop({ required: true }) content!: string;
  @Prop() theme?: string;
  @Prop() onChange?: (s: string) => void;
  @Prop() fullscreenToggled?: () => void;
  @Prop({ default: false }) disableFullscreen!: boolean;

  // Ace Props
  @Prop() readOnly?: boolean;
  @Prop() wrapText?: boolean;

  @Prop() extraClasses?: string;
  @Prop() collapsible?: boolean;

  toggleModalOn() {
    this.fullscreen = true;
  }

  public renderModal() {
    if (!this.fullscreen) {
      return null;
    }

    const nameString = `${this.readOnly ? 'View' : 'Edit'} '${this.name}'`;

    const modalOnHandlers = {
      hidden: () => (this.fullscreen = false)
    };

    return (
      <b-modal
        ref={`code-modal-${this.name}`}
        on={modalOnHandlers}
        hide-footer={true}
        no-close-on-esc={true}
        size="xl no-max-width no-modal-body-padding dark-modal"
        title={nameString}
        visible={this.fullscreen}
      >
        <div class="refinery-code-editor-container__modal width--100percent">{this.renderEditor()}</div>
      </b-modal>
    );
  }

  public renderEditor() {
    // If we don't have valid state, tell the user.
    if (this.content === null) {
      return <h3>Could not display code editor.</h3>;
    }

    const monacoProps: MonacoEditorProps = {
      value: this.content,
      language: languageToAceLangMap[this.lang],
      readOnly: this.readOnly,
      wordWrap: this.wrapText,
      theme: this.theme || 'vs-dark',
      automaticLayout: true,
      onChange: this.onChange
    };

    return (
      // @ts-ignore
      <MonacoEditor key={languageToAceLangMap[this.lang]} ref="editor" props={monacoProps} />
    );
  }

  public render(h: CreateElement): VNode {
    const containerClasses = {
      'refinery-code-editor-container display--flex width--100percent height--100percent position--relative': true,
      'refinery-code-editor-container--read-only': this.readOnly,
      'refinery-code-editor-container--collapsible': this.collapsible,
      [this.extraClasses || '']: Boolean(this.extraClasses)
    };

    const fullscreenOnclick = this.fullscreenToggled || this.toggleModalOn;

    const fullscreenButton = (
      <div
        class="refinery-code-editor-container__expand-button"
        title="Make editor fullscreen"
        on={{ click: () => fullscreenOnclick() }}
      >
        <span class="fa fa-expand" />
      </div>
    );

    return (
      <div class={containerClasses}>
        {this.renderEditor()}
        {!this.disableFullscreen && fullscreenButton}
        {this.renderModal()}
      </div>
    );
  }
}

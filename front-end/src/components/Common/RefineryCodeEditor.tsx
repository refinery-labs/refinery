import copy from 'copy-to-clipboard';
import { CreateElement, VNode } from 'vue';
import { Component, Prop, Vue } from 'vue-property-decorator';
import { EditorProps } from '@/types/component-types';
import { SupportedLanguage } from '@/types/graph';
import { languageToAceLangMap } from '@/types/project-editor-types';
import { MonacoEditorProps } from '@/lib/monaco-editor-props';

@Component
export default class RefineryCodeEditor extends Vue implements EditorProps {
  fullscreen = false;
  linkCopiedIconVisible = false;

  @Prop({ required: true }) name!: string;
  @Prop({ required: true }) lang!: SupportedLanguage | 'text' | 'json' | 'markdown' | 'shell';
  @Prop({ required: true }) content!: string;
  @Prop({ required: false }) originalContent!: string;
  @Prop() theme?: string;
  @Prop() onChange?: (s: string) => void;
  @Prop() fullscreenToggled?: () => void;
  @Prop({ default: false }) disableFullscreen!: boolean;
  @Prop({ default: false }) tailOutput!: boolean;
  @Prop({ default: false }) diffEditor!: boolean;
  @Prop({ default: false }) lineNumbers!: boolean;

  // Ace Props
  @Prop() readOnly?: boolean;
  @Prop() wrapText?: boolean;

  @Prop() extraClasses?: string;
  @Prop() collapsible?: boolean;
  private editor: { MonacoEditor: Function } | null = null;

  async mounted() {
    this.editor = await import('@/lib/MonacoEditor');
  }

  toggleModalOn() {
    this.fullscreen = true;
  }

  copyContentsToClipboard() {
    copy(this.content);

    // Hack to visually give the user feedback
    this.linkCopiedIconVisible = true;
    setTimeout(() => (this.linkCopiedIconVisible = false), 1000);
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
      onChange: this.onChange,
      tailOutput: this.tailOutput,
      diffEditor: this.diffEditor,
      original: this.originalContent,
      lineNumbers: this.lineNumbers
    };

    if (this.editor === null) {
      return 'Loading Editor...';
    }

    return (
      <this.editor.MonacoEditor
        key={`${languageToAceLangMap[this.lang]}${this.readOnly ? '-read-only' : ''}`}
        ref="editor"
        props={monacoProps}
      />
    );
  }

  renderClipboardButton(visible: boolean) {
    if (visible) {
      return <span class="fas fa-clipboard-check" />;
    }

    return <span class="far fa-clipboard" />;
  }

  public render(h: CreateElement): VNode {
    const containerClasses = {
      'refinery-code-editor-container display--flex width--100percent height--100percent position--relative': true,
      'refinery-code-editor-container--read-only': this.readOnly,
      'refinery-code-editor-container--collapsible': this.collapsible,
      [this.extraClasses || '']: Boolean(this.extraClasses)
    };

    const fullscreenOnclick = this.fullscreenToggled || this.toggleModalOn;

    const clipboardClasses = {
      'refinery-code-editor-container__expand-button': true,
      // Kinda nasty way to handle moving this button whenever the fullscreen button is disabled...
      'refinery-code-editor-container__expand-button--upper': !this.disableFullscreen,
      'refinery-code-editor-container__expand-button--lower': this.disableFullscreen
    };

    const copyToClipboardButton = (
      <div
        class={clipboardClasses}
        title="Copy editor contents to clipboard"
        on={{ click: () => this.copyContentsToClipboard() }}
      >
        {this.renderClipboardButton(this.linkCopiedIconVisible)}
      </div>
    );

    const fullscreenButton = (
      <div
        class="refinery-code-editor-container__expand-button refinery-code-editor-container__expand-button--lower"
        title="Make editor fullscreen"
        on={{ click: () => fullscreenOnclick() }}
      >
        <span class="fa fa-expand" />
      </div>
    );

    return (
      <div class={containerClasses}>
        {this.renderEditor()}
        {copyToClipboardButton}
        {!this.disableFullscreen && fullscreenButton}
        {this.renderModal()}
      </div>
    );
  }
}

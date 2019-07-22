import { CreateElement, VNode } from 'vue';
import { Component, Prop, Vue } from 'vue-property-decorator';
// @ts-ignore
import elementResizeDetector from 'element-resize-detector';
import { EditorProps } from '@/types/component-types';
import { SupportedLanguage } from '@/types/graph';
import { languageToAceLangMap } from '@/types/project-editor-types';
import MonacoEditor from '@/lib/MonacoEditor';

@Component
export default class RefineryCodeEditor extends Vue implements EditorProps {
  @Prop({ required: true }) name!: string;
  @Prop({ required: true }) lang!: SupportedLanguage | 'text' | 'json';
  @Prop({ required: true }) content!: string;
  @Prop() theme?: string;
  @Prop() onChange?: (s: string) => void;
  @Prop() onChangeContext?: (c: { value: string; this: any }) => void;

  // Ace Props
  @Prop() readOnly?: boolean;
  @Prop() wrapText?: boolean;

  @Prop() extraClasses?: string;
  @Prop() collapsible?: boolean;

  mounted() {
    if (!this.$refs.editorParent || !this.$refs.editor) {
      console.warn('Could not setup resize detected for code editor', name);
      return;
    }

    //@ts-ignore
    const editor = this.$refs.editor.getEditor();

    if (this.readOnly) {
      editor.updateOptions({
        readOnly: true
      });
    }

    // Annoying but we can't easily use the normal change handlers...
    // Because the library doesn't seem to be consuming them correctly?
    editor.onDidChangeModelContent(() => {
      const value = editor.getValue();
      if (this.content !== value) {
        this.onChange && this.onChange(value);
      }
    });

    const resizeDetector = elementResizeDetector({
      // This is a faster performance mode that is available
      // Unfortunately this doesn't work for all cases, so we're falling back on the slower version.
      // strategy: 'scroll'
    });

    resizeDetector.listenTo(this.$refs.editorParent, () => {
      // @ts-ignore
      this.$refs.editor.getEditor().layout();
    });

    setTimeout(() => {
      // @ts-ignore
      this.$refs.editor.getEditor().layout();
    }, 1000);
  }

  public renderEditor() {
    // If we don't have valid state, tell the user.
    if (this.content === null) {
      return <h3>Could not display code editor.</h3>;
    }

    const monacoProps = {
      value: this.content,
      language: languageToAceLangMap[this.lang],
      readOnly: this.readOnly,
      wordWrap: this.wrapText,
      theme: this.theme || 'vs-dark',
      automaticLayout: true
    };

    const monacoClasses = {
      'width--100percent flex-grow--1 display--flex': true
    };

    return (
      // @ts-ignore
      <MonacoEditor ref="editor" class={monacoClasses} props={monacoProps} />
    );
  }

  public render(h: CreateElement): VNode {
    const containerClasses = {
      'refinery-code-editor-container width--100percent height--100percent display--flex flex-grow--1': true,
      'refinery-code-editor-container--read-only': this.readOnly,
      'refinery-code-editor-container--collapsible': this.collapsible,
      [this.extraClasses || '']: Boolean(this.extraClasses)
    };

    return (
      <div ref="editorParent" class={containerClasses}>
        {this.renderEditor()}
      </div>
    );
  }
}

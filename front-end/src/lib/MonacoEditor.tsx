import * as monaco from 'monaco-editor/esm/vs/editor/editor.api';
import Vue from 'vue';
import Component from 'vue-class-component';
import { Prop, Watch } from 'vue-property-decorator';
// @ts-ignore
import elementResizeDetector from 'element-resize-detector';
import IModelContentChangedEvent = monaco.editor.IModelContentChangedEvent;
import { timeout } from '@/utils/async-utils';
import { MonacoEditorProps } from '@/lib/monaco-editor-props';

@Component
export class MonacoEditor extends Vue implements MonacoEditorProps {
  editor?: any;
  lastEditorHeight?: number;
  lastEditorContentsLength?: number;
  tailingEnabled?: boolean;

  @Prop() public readOnly?: boolean;
  @Prop() public original?: string;
  @Prop({ required: true }) public value!: string;
  @Prop({ default: 'vs-dark' }) public theme!: string;
  @Prop() public options?: {};
  @Prop() public language?: string;
  @Prop({ default: false }) public diffEditor!: boolean;
  @Prop({ default: false }) public wordWrap!: boolean;
  @Prop({ default: false }) public automaticLayout!: boolean;
  @Prop({ default: false }) public tailOutput!: boolean;

  @Prop() onChange?: (s: string) => void;

  @Watch('options', { deep: true })
  public watchOptions(newOptions?: {}) {
    if (this.editor) {
      const editor = this.getModifiedEditor();
      editor.updateOptions(newOptions);
    }
  }

  @Watch('value')
  public watchValue(newValue: string) {
    if (this.editor) {
      const editor = this.getModifiedEditor();
      if (newValue !== editor.getValue()) {
        editor.setValue(newValue);
      }

      this.onTailedContentRefreshed();
    }
  }

  @Watch('original')
  public watchOriginal(newOriginal: string) {
    if (this.diffEditor && this.editor) {
      const editor = this.getOriginalEditor();
      if (newOriginal !== editor.getValue()) {
        editor.setValue(newOriginal);
      }
    }
  }

  @Watch('language')
  public watchLanguage(newLanguage?: string) {
    if (this.editor) {
      const editor = this.getModifiedEditor();
      monaco.editor.setModelLanguage(editor.getModel(), newLanguage || 'text');
    }
  }

  @Watch('theme')
  public watchTheme(newTheme?: string) {
    if (this.editor) {
      monaco.editor.setTheme(newTheme || 'vs-dark');
    }
  }

  onTailedContentRefreshed() {
    const editor = this.getModifiedEditor();
    if (this.tailOutput) {
      const characterCount = editor.getValue().length;
      const editorPreviouslyHadContent = this.lastEditorContentsLength !== undefined;
      const newContentIsShorter =
        this.lastEditorContentsLength !== undefined && characterCount < this.lastEditorContentsLength;

      // If we detected that we suddenly have less content in the editor
      // than we did previously that means that we are almost certainly
      // starting a new run and can re-enable tailing!
      if (editorPreviouslyHadContent && newContentIsShorter) {
        this.tailingEnabled = true;
      }

      this.lastEditorContentsLength = characterCount;
    }

    // We use tailingEnabled instead of the prop because
    // we want to disable tailing if the user has attempted to scroll
    // up. Vue doesn't like you mutating props so we pull the state internally.
    if (this.tailingEnabled) {
      // Auto-scroll to the bottom
      const lineCount = editor.getModel().getLineCount();
      editor.revealLine(lineCount);
    }
  }

  relayoutEditor() {
    this.editor.layout();
  }

  mounted() {
    this.initMonaco();
  }

  beforeDestroy() {
    this.editor && this.editor.dispose();
  }

  initMonaco() {
    // Annoying... But this satisfies the Typescript beast.
    const wordWrap: 'off' | 'on' | 'wordWrapColumn' | 'bounded' = this.wordWrap ? 'on' : 'off';

    const options = Object.assign(
      {},
      {
        value: this.value,
        theme: this.theme,
        language: this.language,
        readOnly: this.readOnly,
        wordWrap: wordWrap
        // This is disabled because the library we use has better performance.
        // automaticLayout: this.automaticLayout
      },
      this.options
    );

    if (this.diffEditor) {
      this.editor = monaco.editor.createDiffEditor(this.$el as HTMLElement, options);

      const originalModel = monaco.editor.createModel(this.original || '', this.language);
      const modifiedModel = monaco.editor.createModel(this.value, this.language);
      this.editor.setModel({
        original: originalModel,
        modified: modifiedModel
      });
    } else {
      this.editor = monaco.editor.create(this.$el as HTMLElement, options);
    }

    // @event `change`
    const editor = this.getModifiedEditor();
    editor.onDidChangeModelContent((event: IModelContentChangedEvent) => {
      const value = editor.getValue();
      if (this.value !== value) {
        this.$emit('change', value, event);
        this.onChange && this.onChange(value);
      }
    });

    // Enable tailing if it was set
    this.lastEditorHeight = 0;
    if (this.tailOutput) {
      this.tailingEnabled = true;
    }

    // This is used with the tailing of output functionality to calculate if
    // a user scrolled while the output was being tailed. If they have and it
    // wasn't programmatically-caused then we need to stop tailing!
    editor.onDidScrollChange((event: monaco.IScrollEvent) => {
      if (this.lastEditorHeight === undefined) {
        return;
      }

      if (this.lastEditorHeight > event.scrollTop) {
        this.tailingEnabled = false;
      }

      this.lastEditorHeight = event.scrollTop;
    });

    editor.updateOptions({
      insertSpaces: true,
      readOnly: this.readOnly
    });

    const resizeDetector = elementResizeDetector({
      // This is a faster performance mode that is available
      // Unfortunately this doesn't work for all cases, so we're falling back on the slower version.
      // strategy: 'scroll'
    });

    resizeDetector.listenTo(this.$refs.editorParent, () => {
      this.relayoutEditor();
    });

    this.$emit('editorDidMount', this.editor);

    this.relayoutEditor();

    // Attempt to relayout the component, once.
    setTimeout(async () => {
      let attempts = 0;
      await timeout(1000);
      while (!this.$refs.editor && attempts < 10) {
        if (this.$refs.editor) {
          this.relayoutEditor();
          return;
        }
        await timeout(1000);
        attempts++;
      }
    }, 1000);
  }

  getEditor() {
    return this.editor;
  }

  getModifiedEditor() {
    return this.diffEditor ? this.editor.getModifiedEditor() : this.editor;
  }

  getOriginalEditor() {
    return this.diffEditor ? this.editor.getOriginalEditor() : undefined;
  }

  focus() {
    this.editor.focus();
  }

  render() {
    return <div class="ace-hack overflow--hidden" ref="editorParent" />;
  }
}

import * as monaco from 'monaco-editor';
import Vue from 'vue';
import Component from 'vue-class-component';
import { Prop, Watch } from 'vue-property-decorator';
import IModelContentChangedEvent = monaco.editor.IModelContentChangedEvent;

@Component
export default class MonacoEditor extends Vue {
  editor?: any;

  @Prop() public original?: string;
  @Prop({ required: true }) public value!: string;
  @Prop({ default: 'vs-dark' }) public theme!: string;
  @Prop() public options?: {};
  @Prop() public language?: string;
  @Prop({ default: false }) public diffEditor!: boolean;

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

  mounted() {
    this.initMonaco();
  }

  beforeDestroy() {
    this.editor && this.editor.dispose();
  }

  initMonaco() {
    const options = Object.assign(
      {},
      {
        value: this.value,
        theme: this.theme,
        language: this.language
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
      }
    });

    this.$emit('editorDidMount', this.editor);
  }

  getEditor() {
    return this.editor;
  }

  getModifiedEditor() {
    return this.diffEditor ? this.editor.getModifiedEditor() : this.editor;
  }

  focus() {
    this.editor.focus();
  }

  render() {
    return <div />;
  }
}

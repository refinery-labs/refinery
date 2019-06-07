<template>
  <div :id="editorId" style="width: 100%; height: 100%;"></div>
</template>
<script>
import Vue from 'vue';

window.define = ace.define;
window.require = ace.require;
// window.ace.config.set( "basePath", require('../../../public/js/') );

// Lord, please help me
export default Vue.component('AceEditor', {
  props: ['editorId', 'content', 'lang', 'theme', 'disabled'],
  data() {
    return {
      editor: Object,
      beforeContent: false
    };
  },
  watch: {
    content(value) {
      if (value !== this.beforeContent) {
        this.editor.setValue(value, 1);
      }
    },
    lang(lang) {
      this.editor.getSession().setMode({
        path: `ace/mode/${lang}`,
        v: Date.now()
      });
    },
    disabled(disabled_boolean) {
      this.editor.setReadOnly(disabled_boolean);
    }
  },
  mounted() {
    const lang = this.lang || 'python';
    const theme = this.theme || 'monokai';
    const disabled = this.disabled || false;

    this.editor = window.ace.edit(this.editorId);
    this.editor.setValue(this.content, 1);

    this.editor.getSession().setMode({
      path: `ace/mode/${lang}`,
      v: Date.now()
    });
    this.editor.setOptions({
      tabSize: 4,
      useSoftTabs: true,
      scrollPastEnd: true,
      enableBasicAutocompletion: true,
      enableLiveAutocompletion: true
    });
    this.editor.setTheme(`ace/theme/${theme}`);

    this.editor.setReadOnly(disabled);

    this.editor.on('change', () => {
      this.beforeContent = this.editor.getValue();
      this.$emit('change-content', this.editor.getValue());
      this.$emit('change-content-context', {
        value: this.editor.getValue(),
        this: this
      });
    });
  }
});
</script>

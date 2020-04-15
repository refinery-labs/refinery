declare module '*.vue' {
  import Vue from 'vue';
  export default Vue;
}

declare module 'cytoscape-dagre' {
  import { Ext } from 'cytoscape';
  export default function register(foo: Object): Ext;
}

declare namespace cytoscape {
  export interface StylesheetHelper {
    instanceString(): string;
    selector(s: string): StylesheetHelper;
    css(value: {}): StylesheetHelper;
    css(name: string, value: {}): StylesheetHelper;
    style(value: {}): StylesheetHelper;
    style(name: string, value: {}): StylesheetHelper;
    generateStyle(cy: Stylesheet): Stylesheet;
    appendToStyle(style: Stylesheet): Stylesheet;
  }

  export interface NodeSingular {
    layoutDimensions(options: { nodeDimensionsIncludeLabels: boolean }): { w: number; h: number };
  }

  export interface NodeCollection {
    layoutPositions(
      layout: cytoscape.CoreEvents,
      options: cytoscape.LayoutPositionOptions,
      fn: (ele: any) => { x: number; y: number }
    ): void;
  }
}
// https://github.com/cytoscape/cytoscape.js/blob/unstable/src/index.js#L44

declare module '@/styles/*.scss' {
  const styles: any;
  export = styles;
}

declare module '@/styles/*.css' {
  const styles: any;
  export = styles;
}

declare module 'vue-intercom' {
  import { PluginObject } from 'vue';

  const VueIntercom: VueIntercomPlugin;
  export default VueIntercom;
  export interface VueIntercomPlugin extends PluginObject<{ appId: string }> {}
}

declare module '@isomorphic-git/lightning-fs';

declare module 'vue-monaco' {
  import { PluginObject } from 'vue';

  const VueMonaco: VueMonacoPlugin;
  export default VueMonaco;
  export interface VueMonacoPlugin extends PluginObject<{ appId: string }> {}
}

declare module 'markdown-it' {
  const MarkdownIt: MarkdownItPlugin;
  export default MarkdownIt;
  export interface MarkdownItPlugin {
    new (): MarkdownItPlugin;
    render(md: string): string;
    renderInline(md: string): string;
  }
}

declare module 'popper' {}

declare module 'vue-native-websocket';

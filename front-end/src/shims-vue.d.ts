
declare module "*.vue" {
  import Vue from "vue";
  export default Vue;
}

declare module "vue-konva" {
  import {PluginFunction, PluginObject} from 'vue';
  const konvaPlugin: PluginObject<{}> | PluginFunction<{}>;
  export default konvaPlugin;
}

declare module "cytoscape-dagre" {
  import {Ext} from 'cytoscape';
  export default function register({}): Ext;
}

declare namespace cytoscape {

  export interface StylesheetHelper {
    instanceString(): string
    selector(s: string): StylesheetHelper
    css(value: {}): StylesheetHelper
    css(name: string, value: {}): StylesheetHelper
    style(value: {}): StylesheetHelper
    style(name: string, value: {}): StylesheetHelper
    generateStyle(cy: Stylesheet): Stylesheet
    appendToStyle(style: Stylesheet): Stylesheet
  }
}
// https://github.com/cytoscape/cytoscape.js/blob/unstable/src/index.js#L44

declare module "@/styles/*.scss" {
  const styles: any;
  export = styles;
}

declare module "@/styles/*.css" {
  const styles: any;
  export = styles;
}

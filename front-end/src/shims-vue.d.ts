declare module "*.vue" {
  import Vue from "vue";
  export default Vue;
}

declare module "vue-konva" {
  import {PluginFunction, PluginObject} from 'vue';
  const konvaPlugin: PluginObject<{}> | PluginFunction<{}>;
  export default konvaPlugin;
}

declare module "@/styles/*.scss" {
  const styles: any;
  export = styles;
}

declare module "@/styles/*.css" {
  const styles: any;
  export = styles;
}

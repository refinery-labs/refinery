import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';

@Component
export default class ProjectSettings extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div class="project-settings-page">
        <h2>Project Settings Page</h2>
        <span>TODO: Add "change project name" feature here</span>
        <span>TODO: Add "change log level" setting</span>
        <router-view />
      </div>
    );
  }
}

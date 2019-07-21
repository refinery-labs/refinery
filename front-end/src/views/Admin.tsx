import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';

@Component
export default class AdminPanel extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div class="admin-panel-page">
        <h2>Secret Admin Panel!</h2>
        <div />
      </div>
    );
  }
}

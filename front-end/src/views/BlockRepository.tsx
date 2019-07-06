import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';

@Component
export default class AdminPanel extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div class="admin-panel-page">
        <h2>Block Repository</h2>
        <b-container>
          <b-row>
            <b-col>1</b-col>

            <b-col>2</b-col>
          </b-row>
        </b-container>
        <router-view />
      </div>
    );
  }
}

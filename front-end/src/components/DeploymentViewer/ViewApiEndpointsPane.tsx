import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';

const deployment = namespace('deployment');

@Component
export default class ViewApiEndpointsPane extends Vue {

  public render(h: CreateElement): VNode {
    return (
      <b-list-group class="view-api-endpoints-pane-container">
        API Endpoints
      </b-list-group>
    );
  }
}

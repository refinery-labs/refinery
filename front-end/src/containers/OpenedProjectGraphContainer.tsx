import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import CytoscapeGraph from '@/components/CytoscapeGraph';
import {
  State,
  Getter,
  Action,
  Mutation,
  namespace
} from 'vuex-class'

@Component
export default class ViewProject extends Vue {
  // @State('foo') stateFoo
  
  public render(h: CreateElement): VNode {
    return (
      <div class="opened-project-graph-container">
        <CytoscapeGraph />
      </div>
    );
  }
}

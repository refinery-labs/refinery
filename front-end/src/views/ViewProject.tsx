import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import CytoscapeGraph from '@/components/CytoscapeGraph';
// @ts-ignore
import complexProject from '../store/fake-project-data/complex-data';
// @ts-ignore
import simpleProject from '../store/fake-project-data/simple-data';
import {generateCytoscapeElements, generateCytoscapeStyle} from '@/lib/refinery-to-cytoscript-converter';

@Component
export default class ViewProject extends Vue {
  public render(h: CreateElement): VNode {
    const elements = generateCytoscapeElements(complexProject);
    
    const stylesheet = generateCytoscapeStyle();
    
    return (
      <div class="view-project-page">
        {/*<h2>View Project</h2>*/}
        {/*Id: {this.$route.params.projectId}*/}
        {/*<router-view />*/}
        <CytoscapeGraph props={{elements, stylesheet}} />
      </div>
    );
  }
}

import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { WorkflowState } from '@/types/graph';
import { blockTypeToEditorComponentLookup } from '@/constants/project-editor-constants';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import ViewDeployedBlockPane from '@/components/DeploymentViewer/ViewDeployedBlockPane';

const viewBlock = namespace('viewBlock');
const deploymentExecutions = namespace('deploymentExecutions');

@Component
export default class ViewDeployedBlockLogsPane extends Vue {
  @viewBlock.State selectedNode!: WorkflowState | null;

  public renderExecutionDetails() {
    return <div>Details here</div>;
  }

  public render(h: CreateElement): VNode {
    return (
      <div class="show-block-container">
        <b-card no-body={true} class="overflow-hidden mb-0">
          <b-tabs nav-class="nav-justified" card={true} content-class="padding--none">
            <b-tab title="first" active={true} no-body={true}>
              <template slot="title">
                <span>
                  Execution Details
                  {/*<em class="fas fa-code" />*/}
                </span>
              </template>
              {this.renderExecutionDetails()}
            </b-tab>
            <b-tab title="second" no-body={true}>
              <template slot="title">
                <span>
                  Selected Block
                  {/*<em class="fas fa-code" />*/}
                </span>
              </template>
              <ViewDeployedBlockPane />
            </b-tab>
          </b-tabs>
        </b-card>
      </div>
    );
  }
}

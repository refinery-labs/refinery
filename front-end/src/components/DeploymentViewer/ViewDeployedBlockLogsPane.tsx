import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import moment from 'moment';
import { SupportedLanguage, WorkflowState } from '@/types/graph';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import ViewDeployedBlockPane from '@/components/DeploymentViewer/ViewDeployedBlockPane';
import { EditorProps } from '@/types/component-types';
import { ExecutionStatusType, GetProjectExecutionLogsResult } from '@/types/api-types';
import { ProductionExecution } from '@/types/deployment-executions-types';

const viewBlock = namespace('viewBlock');
const deploymentExecutions = namespace('deploymentExecutions');

function formatDataForAce(data: any) {
  if (data === '') {
    return '';
  }

  if (typeof data === 'number') {
    return data.toString(10);
  }

  return JSON.stringify(data, null, '  ') || '';
}

function executionTypeToString(executionType: ExecutionStatusType) {
  if (executionType === ExecutionStatusType.EXCEPTION) {
    return 'Uncaught Exception';
  }

  if (executionType === ExecutionStatusType.CAUGHT_EXCEPTION) {
    return 'Caught Exception';
  }

  if (executionType === ExecutionStatusType.RETURN) {
    return 'Success';
  }

  return 'Unknown';
}

@Component
export default class ViewDeployedBlockLogsPane extends Vue {
  @viewBlock.State selectedNode!: WorkflowState | null;

  @deploymentExecutions.State selectedExecutionIndexForNode!: number;

  @deploymentExecutions.Getter getAllExecutionsForNode!: GetProjectExecutionLogsResult[] | null;
  @deploymentExecutions.Getter getSelectedExecutionForNode!: GetProjectExecutionLogsResult | null;

  @deploymentExecutions.Mutation setSelectedExecutionIndexForNode!: (i: number) => void;

  public renderExecutionLabels(execution: GetProjectExecutionLogsResult) {
    const durationSinceUpdated = moment.duration(-moment().diff(execution.timestamp * 1000)).humanize(true);
    return (
      <div class="text-align--left">
        <label class="text-bold">Time: &nbsp;</label>
        <label> {durationSinceUpdated}</label>
        <br />
        <label class="text-bold">Status: &nbsp;</label>
        <label> {executionTypeToString(execution.type)}</label>
        <br />
        <label class="text-bold">Log Id: &nbsp;</label>
        <label style="font-size: 0.8rem"> {execution.id}</label>
      </div>
    );
  }

  public renderLogLinks(execution: ProductionExecution) {}

  renderCodeEditor(label: string, name: string, content: string, json: boolean) {
    const editorProps: EditorProps = {
      name,
      content,
      lang: json ? SupportedLanguage.NODEJS_8 : 'text',
      readOnly: true,
      wrapText: true
    };

    return (
      <div class="display--flex flex-direction--column">
        <label class="d-block padding-top--normal">{label}:</label>
        <div class="show-block-container__code-editor--small">
          <RefineryCodeEditor props={editorProps} />
        </div>
      </div>
    );
  }

  public renderExecutionDetails() {
    if (!this.getSelectedExecutionForNode) {
      return <div>Please select an execution.</div>;
    }

    const executionData = this.getSelectedExecutionForNode.data;

    return (
      <div class="display--flex flex-direction--column">
        {this.renderExecutionLabels(this.getSelectedExecutionForNode)}
        {this.renderCodeEditor('Input Data', 'input-data', formatDataForAce(executionData.input_data), true)}
        {this.renderCodeEditor('Execution Output', 'output', executionData.output || '', false)}
        {this.renderCodeEditor('Return Data', 'return-data', formatDataForAce(executionData.return_data), true)}
        {/*{this.renderLogLinks()}*/}
      </div>
    );
  }

  public renderExecutionDropdown() {
    if (!this.getAllExecutionsForNode) {
      return null;
    }

    if (this.getAllExecutionsForNode.length === 1) {
      // TODO: Show something about the current execution being singular?
      return null;
    }

    const invocationItemList = this.getAllExecutionsForNode.map((exec, i) => {
      const onHandlers = {
        // Sets the current index to be active
        click: () => this.setSelectedExecutionIndexForNode(i)
      };

      const isActive = this.selectedExecutionIndexForNode === i;

      return (
        <b-dropdown-item on={onHandlers} active={isActive}>
          Invocation #{i}
        </b-dropdown-item>
      );
    });

    return (
      <b-dropdown right text={`Invocation #${this.selectedExecutionIndexForNode}`} variant="primary" class="m-2">
        {invocationItemList}
      </b-dropdown>
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <div class="show-block-container">
        <b-card no-body={true} class="overflow-hidden mb-0">
          <b-tabs nav-class="nav-justified" card={true} content-class="padding--none disgusting-card-offset">
            <b-tab title="first" active={true} no-body={true}>
              <template slot="title">
                <span>
                  Execution Details
                  {/*<em class="fas fa-code" />*/}
                </span>
              </template>
              <div class="show-block-container container">
                <div class="mb-3 padding-top--big text-align--left show-block-container__form--normal">
                  <div class="scrollable-pane-container padding-left--normal padding-right--normal">
                    {this.renderExecutionDropdown()}
                    {this.renderExecutionDetails()}
                  </div>
                </div>
              </div>
            </b-tab>
            <b-tab title="second" no-body={true}>
              <template slot="title">
                <span>
                  Selected Block
                  {/*<em class="fas fa-code" />*/}
                </span>
              </template>
              <div class="shift-block-nastily-into-tabs">
                <ViewDeployedBlockPane />
              </div>
            </b-tab>
          </b-tabs>
        </b-card>
      </div>
    );
  }
}

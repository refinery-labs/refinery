import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import moment from 'moment';
import { SupportedLanguage, WorkflowState } from '@/types/graph';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import ViewDeployedBlockPane from '@/components/DeploymentViewer/ViewDeployedBlockPane';
import { EditorProps, LoadingContainerProps } from '@/types/component-types';
import {ExecutionLogContents, ExecutionStatusType, GetProjectExecutionLogsResult} from '@/types/api-types';
import {BlockExecutionGroup, BlockExecutionLogContentsByLogId} from '@/types/deployment-executions-types';
import Loading from '@/components/Common/Loading.vue';

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

function executionTypeToVariable(executionType: ExecutionStatusType) {
  if (executionType === ExecutionStatusType.EXCEPTION) {
    return 'danger';
  }

  if (executionType === ExecutionStatusType.CAUGHT_EXCEPTION) {
    return 'warning';
  }

  if (executionType === ExecutionStatusType.SUCCESS) {
    return 'success';
  }

  return 'info';
}

function executionTypeToString(executionType: ExecutionStatusType) {
  if (executionType === ExecutionStatusType.EXCEPTION) {
    return 'Uncaught Exception';
  }

  if (executionType === ExecutionStatusType.CAUGHT_EXCEPTION) {
    return 'Caught Exception';
  }

  if (executionType === ExecutionStatusType.SUCCESS) {
    return 'Success';
  }

  return 'Unknown';
}

@Component
export default class ViewDeployedBlockLogsPane extends Vue {
  @viewBlock.State selectedNode!: WorkflowState | null;

  @deploymentExecutions.State selectedBlockExecutionLog!: string;
  @deploymentExecutions.State blockExecutionLogByLogId!: BlockExecutionLogContentsByLogId;
  @deploymentExecutions.State isFetchingLogs!: boolean;

  @deploymentExecutions.Getter getBlockExecutionGroupForSelectedBlock!: BlockExecutionGroup | null;
  @deploymentExecutions.Getter getAllLogIdsForSelectedBlock!: string[] | null;
  @deploymentExecutions.Getter currentlySelectedLogId!: string | null;
  @deploymentExecutions.Getter getLogForSelectedBlock!: ExecutionLogContents | null;

  @deploymentExecutions.Mutation setSelectedBlockExecutionLog!: (logId: string) => void;

  @deploymentExecutions.Action fetchMoreLogsForSelectedBlock!: () => void;

  public renderExecutionLabels(execution: ExecutionLogContents) {
    const durationSinceUpdated = moment.duration(-moment().diff(execution.timestamp * 1000)).humanize(true);
    return (
      <div class="text-align--left">
        <label class="text-bold">Time: &nbsp;</label>
        <label> {durationSinceUpdated}</label>
        <br />
        <label class="text-bold">Status: &nbsp;</label>
        <label>
          <b-badge variant={executionTypeToVariable(execution.type)} pill>
            {executionTypeToString(execution.type)}
          </b-badge>
        </label>
        <br />
        <label class="text-bold">Log Id: &nbsp;</label>
        <label style="font-size: 0.8rem"> {execution.log_id}</label>
      </div>
    );
  }

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
        <div class="text-align--left run-lambda-container__text-label">
          <label class="text-light padding--none mt-0 mb-0 ml-2">
            {label}:
          </label>
        </div>
        <div class="show-block-container__code-editor--small">
          <RefineryCodeEditor props={editorProps} />
        </div>
      </div>
    );
  }

  public renderExecutionDetails() {

    const executionData = this.getLogForSelectedBlock;

    if (!this.selectedBlockExecutionLog && !executionData && !this.isFetchingLogs) {
      return <div>Missing Executions for block. This should never happen. :(</div>;
    }

    // We have a valid section but no long, hopefully we're loading ;)
    if (!executionData) {
      const loadingProps: LoadingContainerProps = {
        show: true,
        label: 'Loading execution logs...'
      };
      return (
        <div style="margin-top: 60px; min-height: 60px">
          <Loading props={loadingProps} />
        </div>
      );
    }

    return (
      <div class="display--flex flex-direction--column">
        {this.renderExecutionLabels(executionData)}
        {this.renderCodeEditor('Block Input Data', 'input-data', formatDataForAce(executionData.input_data), true)}
        {this.renderCodeEditor('Execution Output', 'output', executionData.program_output || '', false)}
        {this.renderCodeEditor('Return Data', 'return-data', formatDataForAce(executionData.return_data), true)}
        {this.renderCodeEditor('Backpack Data', 'backpack-data', formatDataForAce(executionData.backpack), true)}
        {/*{this.renderLogLinks()}*/}
      </div>
    );
  }

  public renderExecutionDropdown() {
    const nodeExecutions = this.getBlockExecutionGroupForSelectedBlock;
    const logIds = this.getAllLogIdsForSelectedBlock;
    if (!nodeExecutions || !logIds) {
      return null;
    }

    if (nodeExecutions.totalExecutionCount <= 1) {
      // TODO: Show something about the current execution being singular?
      return null;
    }

    const onHandlers = {
      // Sets the current index to be active
      change: (logId: string) => {
        if (logId === 'load-more') {
          this.fetchMoreLogsForSelectedBlock();
          return;
        }

        this.setSelectedBlockExecutionLog(logId);
      }
    };

    const invocationItemList = logIds.map((logId, i) => ({
      value: logId,
      text: `Invocation #${i + 1} (${executionTypeToString(this.blockExecutionLogByLogId[logId].type)})`
    }));

    if (nodeExecutions.totalExecutionCount !== logIds.length) {
      invocationItemList.push({
        value: 'load-more',
        text: 'Load More Executions...'
      });
    }

    return (
      <b-form-select
        class="padding--small mt-2 mb-2"
        value={this.currentlySelectedLogId}
        on={onHandlers}
        options={invocationItemList}
      />
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <div class="display--flex flex-direction--column">
        <b-tabs nav-class="nav-justified" content-class="padding--none">
          <b-tab title="first" active={true} no-body={true}>
            <template slot="title">
              <span>
                Execution Details
                {/*<em class="fas fa-code" />*/}
              </span>
            </template>
            <div class="show-block-container container">
              <div class="mb-3 mt-3 text-align--left show-block-container__form show-block-container__form--normal">
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
            <ViewDeployedBlockPane />
          </b-tab>
        </b-tabs>
      </div>
    );
  }
}

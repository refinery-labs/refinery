import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { SupportedLanguage, WorkflowState } from '@/types/graph';
import RefineryCodeEditor from '@/components/Common/RefineryCodeEditor';
import ViewDeployedBlockPane from '@/components/DeploymentViewer/ViewDeployedBlockPane';
import { EditorProps, LoadingContainerProps } from '@/types/component-types';
import { BlockExecutionGroup, BlockExecutionLogContentsByLogId } from '@/types/deployment-executions-types';
import Loading from '@/components/Common/Loading.vue';
import { ExecutionLogContents, ExecutionLogMetadata, ExecutionStatusType } from '@/types/execution-logs-types';
import { getFriendlyDurationSinceString } from '@/utils/time-utils';

const viewBlock = namespace('viewBlock');
const deploymentExecutions = namespace('deploymentExecutions');

function formatDataForAce(data: any) {
  if (data === '' || data === null || data === undefined) {
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

  @deploymentExecutions.State blockExecutionLogByLogId!: BlockExecutionLogContentsByLogId;
  @deploymentExecutions.State isFetchingLogs!: boolean;
  @deploymentExecutions.State isFetchingMoreLogs!: boolean;

  @deploymentExecutions.Getter getBlockExecutionGroupForSelectedBlock!: BlockExecutionGroup | null;
  @deploymentExecutions.Getter getAllLogMetadataForSelectedBlock!: ExecutionLogMetadata[] | null;
  @deploymentExecutions.Getter currentlySelectedLogId!: string | null;
  @deploymentExecutions.Getter getLogForSelectedBlock!: ExecutionLogContents | null;

  @deploymentExecutions.Action fetchMoreLogsForSelectedBlock!: () => void;
  @deploymentExecutions.Action selectLogByLogId!: (logId: string) => void;

  public renderExecutionLabels(execution: ExecutionLogContents | null) {
    // Return stubbed UI if the execution data is null...
    if (!execution) {
      return (
        <div class="text-align--left row">
          <b-col xl={3}>
            <label class="text-bold">Time: &nbsp;</label>
            <label> Unknown</label>
          </b-col>
          <b-col xl={3}>
            <label class="text-bold">Status: &nbsp;</label>
            <label>
              <b-badge variant="secondary" pill>
                Unknown
              </b-badge>
            </label>
          </b-col>
          <b-col xl={6}>
            <label class="text-bold">Log Id: &nbsp;</label>
            <label style="font-size: 0.8rem"> Unknown</label>
          </b-col>
        </div>
      );
    }

    const durationSinceUpdated = getFriendlyDurationSinceString(execution.timestamp * 1000);
    return (
      <div class="text-align--left row">
        <b-col xl={3}>
          <label class="text-bold">Time: &nbsp;</label>
          <label> {durationSinceUpdated}</label>
        </b-col>
        <b-col xl={3}>
          <label class="text-bold">Status: &nbsp;</label>
          <label>
            <b-badge variant={executionTypeToVariable(execution.type)} pill>
              {executionTypeToString(execution.type)}
            </b-badge>
          </label>
        </b-col>
        <b-col xl={6}>
          <label class="text-bold">Log Id: &nbsp;</label>
          <label style="font-size: 0.8rem"> {execution.log_id}</label>
        </b-col>
      </div>
    );
  }

  renderCodeEditor(label: string, name: string, content: string, json: boolean) {
    const editorProps: EditorProps = {
      name,
      content,
      lang: json ? SupportedLanguage.NODEJS_8 : 'text',
      readOnly: true,
      wrapText: true,
      extraClasses: 'height--100percent'
    };

    return (
      <div class="display--flex flex-grow--1 flex-direction--column">
        <div class="text-align--left run-lambda-container__text-label">
          <label class="text-light padding--none mt-0 mb-0 ml-2">{label}:</label>
        </div>
        <div class="show-block-container__code-editor--small">
          <RefineryCodeEditor props={editorProps} />
        </div>
      </div>
    );
  }

  public renderExecutionDetails() {
    const executionData = this.getLogForSelectedBlock;

    return (
      <div class="display--flex flex-direction--column">
        {this.renderExecutionLabels(executionData)}
        {this.renderCodeEditor(
          'Block Input Data',
          'input-data',
          formatDataForAce(executionData && executionData.input_data),
          true
        )}
        {this.renderCodeEditor(
          'Execution Output',
          'output',
          (executionData && executionData.program_output) || '',
          false
        )}
        {this.renderCodeEditor(
          'Return Data',
          'return-data',
          formatDataForAce(executionData && executionData.return_data),
          true
        )}
        {this.renderCodeEditor(
          'Backpack Data',
          'backpack-data',
          formatDataForAce(executionData && executionData.backpack),
          true
        )}
        {/*{this.renderLogLinks()}*/}
      </div>
    );
  }

  public renderExecutionDropdown() {
    const nodeExecutions = this.getBlockExecutionGroupForSelectedBlock;
    const logsMetadata = this.getAllLogMetadataForSelectedBlock;

    if (!nodeExecutions || !logsMetadata) {
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

        this.selectLogByLogId(logId);
      }
    };

    const invocationItemList = Object.values(logsMetadata).map((metadata, i) => {
      return {
        value: metadata.log_id,
        text: `Invocation #${i + 1} (${executionTypeToString(metadata.type)})`
      };
    });

    if (nodeExecutions.totalExecutionCount !== logsMetadata.length) {
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
    const executionData = this.getLogForSelectedBlock;

    const isLoading = this.isFetchingLogs || this.isFetchingMoreLogs;

    const loadingProps: LoadingContainerProps = {
      show: false,
      label: 'Loading execution logs...'
    };

    // We have a valid section but no long, hopefully we're loading ;)
    if (!executionData) {
      loadingProps.show = true;
    }

    if (!this.currentlySelectedLogId && !executionData && !isLoading) {
      loadingProps.label = 'Executions are still loading, please wait...';
    }

    return (
      <div class="display--flex flex-direction--column" style="min-width: 340px">
        <b-tabs nav-class="nav-justified" content-class="padding--none">
          <b-tab title="first" active={true} no-body={true}>
            <template slot="title">
              <span>
                Execution Details
                {/*<em class="fas fa-code" />*/}
              </span>
            </template>
            <div class="show-block-container mr-2 ml-2">
              {this.renderExecutionDropdown()}
              <Loading props={loadingProps}>
                <div class="mb-2 text-align--left show-block-container__form show-block-container__form--normal">
                  <div class="scrollable-pane-container padding-left--normal padding-right--normal container">
                    {this.renderExecutionDetails()}
                  </div>
                </div>
              </Loading>
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

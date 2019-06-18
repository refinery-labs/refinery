import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { Execution } from '@/types/api-types';
import { Prop } from 'vue-property-decorator';
import { ViewExecutionsListProps } from '@/types/component-types';
import moment from 'moment';
import { ProductionExecution } from '@/types/deployment-executions-types';

@Component
export default class ViewExecutionsList extends Vue implements ViewExecutionsListProps {
  @Prop({ required: true }) projectExecutions!: ProductionExecution[] | null;
  @Prop({ required: true }) openExecutionGroup!: (id: string) => void;

  public renderExecution(execution: ProductionExecution) {
    const durationSinceUpdated = moment
      .duration(-moment().diff(execution.oldest_observed_timestamp * 1000))
      .humanize(true);

    return (
      <b-list-group-item
        button={true}
        class="d-flex justify-content-between align-items-center"
        on={{ click: () => this.openExecutionGroup(execution.executionId) }}
      >
        <label class="text-muted mb-0 text-align--left" style="width: 80px">
          {durationSinceUpdated}
        </label>
        <div style="width: 80px" class="text-align--right padding-right--small">
          <b-badge variant={execution.error ? 'danger' : 'success'} pill>
            {execution.error ? 'error' : 'pass'}
          </b-badge>
        </div>
        <div style="width: 80px" class="text-align--left">
          <b-badge variant="info" pill>
            {execution.logs.length} execution{execution.logs.length > 1 ? 's' : ''}
          </b-badge>
        </div>
      </b-list-group-item>
    );
  }

  public render(h: CreateElement): VNode {
    const containerClasses = {
      'view-executions-list-container scrollable-pane-container': true
    };

    if (!this.projectExecutions) {
      return (
        <div class={containerClasses}>
          <h4>Please wait while executions are loaded...</h4>
        </div>
      );
    }

    const projectExecutions = this.projectExecutions;

    if (projectExecutions.length === 0) {
      return (
        <div class={containerClasses}>
          <h4>
            There are not any executions of this pipeline. For more information on, please read{' '}
            <a href="https://docs.refinerylabs.io/debugging/" target="_blank">
              these docs
            </a>
            .
          </h4>
        </div>
      );
    }

    return (
      <div class={containerClasses}>
        <b-list-group>{projectExecutions.map(execution => this.renderExecution(execution))}</b-list-group>
      </div>
    );
  }
}

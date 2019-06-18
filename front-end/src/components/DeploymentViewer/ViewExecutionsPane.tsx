import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import { Execution } from '@/types/api-types';

const deploymentExecutions = namespace('deploymentExecutions');

@Component
export default class ViewExecutionsPane extends Vue {
  @deploymentExecutions.State isBusy!: boolean;
  @deploymentExecutions.State projectExecutions!: { [key: string]: Execution } | null;

  @deploymentExecutions.Action openExecutionGroup!: (id: string) => void;

  public renderExecution(key: string, execution: Execution) {
    return (
      <b-list-group-item
        class="d-flex justify-content-between align-items-center"
        on={{ click: () => this.openExecutionGroup(key) }}
      >
        {execution.oldest_observed_timestamp}
        <b-badge variant={execution.error ? 'danger' : 'success'} pill>
          {execution.logs.length}
        </b-badge>
      </b-list-group-item>
    );
  }

  public render(h: CreateElement): VNode {
    const containerClasses = {
      'view-executions-pane-container': true,
      // TODO: Swap this with loading component
      'whirl standard': this.isBusy
    };

    if (!this.projectExecutions) {
      return (
        <div class={containerClasses}>
          <h4>Please wait while executions are loaded...</h4>
        </div>
      );
    }

    return <b-list-group class={containerClasses} />;
  }
}

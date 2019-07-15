import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { Prop } from 'vue-property-decorator';
import { ViewExecutionsListProps } from '@/types/component-types';
import moment from 'moment';
import { ProjectExecution } from '@/types/deployment-executions-types';

@Component
export default class ViewExecutionsList extends Vue implements ViewExecutionsListProps {
  @Prop({ required: true }) projectExecutions!: ProjectExecution[] | null;
  @Prop({ required: true }) selectedProjectExecution!: string | null;
  @Prop({ required: true }) openExecutionGroup!: (id: string) => void;
  @Prop({ required: true }) isBusyRefreshing!: boolean;
  @Prop({ required: true }) showMoreExecutions!: () => void;
  @Prop({ required: true }) hasMoreExecutionsToLoad!: boolean;

  renderStatusPill(count: number, name: string, variant: string) {
    if (count === 0) {
      return null;
    }

    return (
      <b-badge variant={variant} pill>
        {`${count} ${name}`}
      </b-badge>
    );
  }

  public renderExecution(execution: ProjectExecution) {
    const durationSinceUpdated = moment.duration(-moment().diff(execution.oldestTimestamp * 1000)).humanize(true);

    const isActive = execution.executionId === this.selectedProjectExecution;

    const labelClasses = {
      'text-muted mb-0 text-align--left': true,
      'text-white': isActive
    };

    const badgesClasses = {
      'view-executions-list-container__badges': true,
      'text-align--right padding-left--normal padding-right--normal': true,
      'display--flex flex-direction--column': true
    };

    const badges = [
      this.renderStatusPill(execution.errorCount, 'error', 'danger'),
      this.renderStatusPill(execution.caughtErrorCount, 'caught', 'warning'),
      this.renderStatusPill(execution.successCount, 'success', 'success')
    ];

    return (
      <b-list-group-item
        button={true}
        active={isActive}
        class="d-flex justify-content-between align-items-center"
        on={{ click: () => this.openExecutionGroup(execution.executionId) }}
      >
        <label class={labelClasses} style="min-width: 80px">
          {durationSinceUpdated}
        </label>

        <div style="min-width: 80px" class={badgesClasses}>
          {badges}
        </div>
        <div style="min-width: 80px" class="text-align--left">
          <b-badge variant="info" pill>
            {execution.numberOfLogs} execution{execution.numberOfLogs > 1 ? 's' : ''}
          </b-badge>
        </div>
      </b-list-group-item>
    );
  }

  renderLoadButton() {
    if (!this.isBusyRefreshing) {
      return (
        <b-button
          variant="primary"
          on={{ click: this.showMoreExecutions }}
          class="col-10 m-1"
          disabled={!this.hasMoreExecutionsToLoad}
        >
          Load More
        </b-button>
      );
    }

    return (
      <b-button variant="primary" disabled class="col-10 m-1">
        <b-spinner small /> Refreshing...
      </b-button>
    );
  }

  public render(h: CreateElement): VNode {
    const containerClasses = {
      'view-executions-list-container scrollable-pane-container': true,
      'padding--big': false
    };

    if (!this.projectExecutions) {
      containerClasses['padding--big'] = true;

      return (
        <div class={containerClasses}>
          <h4>Please wait while executions are loaded...</h4>
          <h5>(This may take up to 15 seconds)</h5>
        </div>
      );
    }

    const projectExecutions = this.projectExecutions;

    if (Object.keys(projectExecutions).length === 0) {
      return (
        <div class={containerClasses}>
          <h4 style="margin: 10px;">
            There are not any executions of this pipeline yet.
            <br />
            Click on "Code Runner" to manually run a block.
            <br />
            For more information please read{' '}
            <a href="https://docs.refinery.io/debugging/" target="_blank">
              these docs
            </a>
            .
          </h4>
          <h4>
            <b-spinner small /> Polling for execution logs...
          </h4>
        </div>
      );
    }

    return (
      <div class={containerClasses}>
        <b-list-group>
          {Object.values(projectExecutions).map(execution => this.renderExecution(execution))}
        </b-list-group>
        {this.renderLoadButton()}
      </div>
    );
  }
}

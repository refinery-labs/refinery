import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import ViewExecutionsList from '@/components/ViewExecutions/ViewExecutionsList';
import { ViewExecutionsListProps } from '@/types/component-types';
import { ProductionExecution } from '@/types/deployment-executions-types';

const deploymentExecutions = namespace('deploymentExecutions');

@Component
export default class ViewExecutionsPane extends Vue {
  @deploymentExecutions.State isBusy!: boolean;
  @deploymentExecutions.State isFetchingMoreExecutions!: boolean;
  @deploymentExecutions.Getter sortedExecutions!: ProductionExecution[] | null;

  @deploymentExecutions.Action openExecutionGroup!: (id: string) => void;
  @deploymentExecutions.Action getExecutionsForOpenedDeployment!: (resume: boolean) => void;

  public render(h: CreateElement): VNode {
    const containerClasses = {
      'view-executions-pane-container': true,
      // TODO: Swap this with loading component
      'whirl standard': this.isBusy
    };

    const viewExecutionsListProps: ViewExecutionsListProps = {
      openExecutionGroup: this.openExecutionGroup,
      projectExecutions: this.sortedExecutions,
      isBusyRefreshing: this.isFetchingMoreExecutions,
      showMoreExecutions: () => this.getExecutionsForOpenedDeployment(true)
    };

    return (
      <div class={containerClasses}>
        <ViewExecutionsList props={viewExecutionsListProps} />
      </div>
    );
  }
}

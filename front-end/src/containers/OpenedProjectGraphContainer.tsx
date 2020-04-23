import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import CytoscapeGraph from '@/components/CytoscapeGraph';
import { namespace, State } from 'vuex-class';
import { RefineryProject } from '@/types/graph';
import { LayoutOptions } from 'cytoscape';
import { AvailableTransition } from '@/store/store-types';
import { CyElements, CyStyle, CytoscapeGraphProps } from '@/types/cytoscape-types';
import { SIDEBAR_PANE } from '@/types/project-editor-types';
import TourWrapper from '@/lib/Tooltip';
import { DemoWalkthroughStoreModule } from '@/store';
import { DemoTooltipActionType, TooltipType } from '@/types/demo-walkthrough-types';
import { timeout, waitUntil } from '@/utils/async-utils';
import { ProductionExecutionResponse } from '@/types/deployment-executions-types';
import Tooltip from '@/lib/Tooltip';
import { TooltipProps } from '@/types/tooltip-types';
import { RepoCompilationError } from '@/repo-compiler/lib/git-utils';

const project = namespace('project');
const syncProjectRepo = namespace('syncProjectRepo');

@Component
export default class OpenedProjectGraphContainer extends Vue {
  showTooltip = true;
  @project.State openedProject!: RefineryProject | null;
  @project.State selectedResource!: string | null;

  @project.State cytoscapeElements!: CyElements | null;
  @project.State cytoscapeStyle!: CyStyle | null;
  @project.State cytoscapeLayoutOptions!: LayoutOptions | null;
  @project.State cytoscapeConfig!: cytoscape.CytoscapeOptions | null;
  @project.State isAddingSharedFileToCodeBlock!: boolean;

  @project.State isLoadingProject!: boolean;
  @syncProjectRepo.State repoCompilationError!: RepoCompilationError | undefined;
  @project.State isInDemoMode!: boolean;
  @project.State currentTooltip!: number;
  @State windowWidth?: number;

  @project.Getter getValidBlockToBlockTransitions!: AvailableTransition[] | null;
  @project.Getter getCodeBlockIDs!: string[];

  @project.Action clearSelection!: () => void;
  @project.Action selectNode!: (element: string) => void;
  @project.Action selectEdge!: (element: string) => void;
  @project.Action openRightSidebarPane!: (sidebarPane: SIDEBAR_PANE) => void;

  mounted() {
    setTimeout(() => (this.showTooltip = false), 15000);

    if (this.isInDemoMode) {
      // Show the project README if this is demo mode
      this.displayReadMe();
    }
  }

  public displayReadMe() {
    if (!this.openedProject) {
      return;
    }

    if (this.openedProject.readme.trim() === '') {
      return;
    }

    this.openRightSidebarPane(SIDEBAR_PANE.viewReadme);
  }

  public getEnabledNodeIds() {
    if (this.isAddingSharedFileToCodeBlock) {
      return this.getCodeBlockIDs;
    }

    if (!this.getValidBlockToBlockTransitions) {
      return null;
    }

    return this.getValidBlockToBlockTransitions.map(v => v.toNode.id);
  }

  public getDemoWalkthrough() {
    const tourProps: TooltipProps = {
      step: DemoWalkthroughStoreModule.currentHTMLTooltip,
      nextTooltip: DemoWalkthroughStoreModule.nextTooltip,
      skipTooltips: DemoWalkthroughStoreModule.skipWalkthrough
    };

    if (
      DemoWalkthroughStoreModule.currentTooltip &&
      DemoWalkthroughStoreModule.currentTooltip.type == TooltipType.HTMLTooltip
    ) {
      return (
        <div>
          <Tooltip props={tourProps} />
        </div>
      );
    }
    return <div />;
  }

  public render(h: CreateElement): VNode {
    if (this.isLoadingProject) {
      return <h2>Waiting for data...</h2>;
    }

    if (this.repoCompilationError) {
      return (
        <div>
          <h2>Error while compiling graph</h2>
          <p>{this.repoCompilationError.message}</p>
          <h4>{this.repoCompilationError.errorContext && this.repoCompilationError.errorContext.filename}</h4>
          <code>{this.repoCompilationError.errorContext && this.repoCompilationError.errorContext.fileContent}</code>
        </div>
      );
    }

    if (!this.cytoscapeElements || !this.cytoscapeStyle) {
      const errorMessage = 'Graph unable to render, missing data!';
      console.error(errorMessage);
      return <h2>{errorMessage}</h2>;
    }

    // By holding these in the stores, we can compare pointers because the data is "immutable".
    const graphProps: CytoscapeGraphProps = {
      clearSelection: this.clearSelection,
      selectNode: this.selectNode,
      selectEdge: this.selectEdge,
      currentTooltips: DemoWalkthroughStoreModule.cyTooltips,
      loadCyTooltips: DemoWalkthroughStoreModule.loadCyTooltips,
      nextTooltip: DemoWalkthroughStoreModule.nextTooltip,
      elements: this.cytoscapeElements,
      stylesheet: this.cytoscapeStyle,
      layout: this.cytoscapeLayoutOptions,
      config: this.cytoscapeConfig,
      selected: this.selectedResource,
      enabledNodeIds: this.getEnabledNodeIds(),
      backgroundGrid: true,
      windowWidth: this.windowWidth
    };

    const containerClasses = {
      'opened-project-graph-container__project-name display--flex flex-direction--column': true,
      'opened-project-graph-container__project-name--demo padding--small': this.isInDemoMode
    };

    const introTooltip = (
      <b-tooltip
        target="quickstart-guide-button"
        show={this.showTooltip}
        placement="top"
        boundary="viewport"
        triggers="hover"
        boundary-padding={10}
        custom-class="getting-started-tooltip"
      >
        <h4>Welcome to Refinery!</h4>
        Click on a block to start building.
        <br />
        Try adding a block too!
        <br />
        For more help, see the guide below.
      </b-tooltip>
    );

    const demoWalkthrough = this.getDemoWalkthrough();

    const demoButtons = (
      <div>
        <b-button
          variant="primary"
          id="quickstart-guide-button"
          href="https://docs.refinery.io/getting-started/#adding-your-first-block"
          target="_blank"
        >
          View Quickstart Guide
        </b-button>
        <b-button class="ml-2" variant="success" to="/register">
          Signup for Refinery
        </b-button>
      </div>
    );

    return (
      <div class="opened-project-graph-container project-graph-container">
        <div class={containerClasses}>
          {this.isInDemoMode && demoButtons}
          <h4 class="margin-top--normal">
            <i>
              {this.isInDemoMode ? 'Importing: ' : ''}
              {this.openedProject && this.openedProject.name}
            </i>
          </h4>
        </div>
        {this.isInDemoMode && introTooltip}
        {demoWalkthrough}
        <CytoscapeGraph props={graphProps} />
      </div>
    );
  }
}

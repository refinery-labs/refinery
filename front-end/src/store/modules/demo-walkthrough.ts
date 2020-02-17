import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState, StoreType } from '@/store/store-types';
import { CY_TOOLTIP_DEFAULTS, CyTooltip, DemoTooltip, HTMLTooltip, TooltipType } from '@/types/demo-walkthrough-types';
import { CytoscapeCanvasInstance } from '@/lib/cytoscape-canvas';

export interface DemoWalkthroughState {
  currentTooltip: number;
  tooltips: DemoTooltip[];
}

export const baseState: DemoWalkthroughState = {
  currentTooltip: 0,
  tooltips: [
    {
      type: TooltipType.HTMLTooltip,
      visible: true,
      tooltip: {
        target: '.project-sidebar-container',
        header: {
          title: 'API Response'
        },
        content:
          'Once your Code Block has done what it needs to do, you can then send a response to the caller of your endpoint. The response will contain whatever JSON data you returned from the last connected Code Block.'
      }
    },
    {
      type: TooltipType.CyTooltip,
      visible: false,
      tooltip: {
        ...CY_TOOLTIP_DEFAULTS,
        id: 'a660c1d8-5534-4138-8729-9eec8f252b69',
        header: 'API Endpoint',
        body:
          'Using refinery, it is super fast to create an HTTP endpoint that is accessible to the Internet. You start with an API Endpoint block.'
      }
    },
    {
      type: TooltipType.CyTooltip,
      visible: false,
      tooltip: {
        ...CY_TOOLTIP_DEFAULTS,
        id: 'b7f55a48-f9d6-4a41-8b8e-2c8fc4b6d413',
        header: 'The Code',
        body:
          'Connecting a Code Block to an API Endpoint will let you process any data that was sent. For example, you might want to do something with the query parameters.'
      }
    }
  ]
};

const initialState = deepJSONCopy(baseState);

// We need to leave this as a "dynamic" module so that we can use the fancy `this` rebinding. Otherwise we have to use
// The old school `context.commit` and `context.dispatch` style syntax.
@Module({ namespaced: true, name: StoreType.demoWalkthrough })
export class DemoWalkthroughStore extends VuexModule<ThisType<DemoWalkthroughState>, RootState>
  implements DemoWalkthroughState {
  public currentTooltip: number = initialState.currentTooltip;
  public tooltips: DemoTooltip[] = initialState.tooltips;

  get currentCyTooltips(): CyTooltip[] {
    return this.tooltips.filter(t => t.visible && t.type == TooltipType.CyTooltip).map(t => t.tooltip as CyTooltip);
  }

  get currentHtmlTooltips(): HTMLTooltip[] {
    return this.tooltips.filter(t => t.visible && t.type == TooltipType.HTMLTooltip).map(t => t.tooltip as HTMLTooltip);
  }

  @Mutation
  public resetState() {
    resetStoreState(this, baseState);
  }

  @Mutation
  public setTooltipPosition(i: number, pos: cytoscape.Position) {}

  @Mutation
  public loadCyTooltips(cy: cytoscape.Core) {
    const tooltips = [...this.tooltips];

    for (let i = 0; i < tooltips.length; i++) {
      const t = tooltips[i];
      if (t.type != TooltipType.CyTooltip) {
        continue;
      }

      let cyTooltip = t.tooltip as CyTooltip;
      const pos = cy.getElementById(cyTooltip.id).position();
      if (pos) {
        cyTooltip.x = pos.x;
        cyTooltip.y = pos.y;
        tooltips[i].tooltip = cyTooltip;
      }
    }

    this.tooltips = tooltips;
  }

  // This is able to call a Mutator via the `this` context because of magic.
  @Mutation
  public nextTooltip() {
    const tooltips = [...this.tooltips];
    tooltips[this.currentTooltip].visible = false;

    const nextCurrentTooltip = this.currentTooltip + 1;
    if (nextCurrentTooltip < this.tooltips.length) {
      tooltips[this.currentTooltip + 1].visible = true;

      this.currentTooltip = nextCurrentTooltip;
      this.tooltips = tooltips;
    }
  }
}

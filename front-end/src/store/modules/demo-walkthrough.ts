import { Action, Module, Mutation, VuexModule } from 'vuex-module-decorators';
import { resetStoreState } from '@/utils/store-utils';
import { deepJSONCopy } from '@/lib/general-utils';
import { RootState, StoreType } from '@/store/store-types';
import { DemoTooltip, TooltipType } from '@/types/demo-walkthrough-types';

export interface DemoWalkthroughState {
  currentTooltip: number;
  tooltips: DemoTooltip[];
  tooltipsLoaded: boolean;
}

export const baseState: DemoWalkthroughState = {
  currentTooltip: 0,
  tooltips: [],
  tooltipsLoaded: false
};

const initialState = deepJSONCopy(baseState);

// We need to leave this as a "dynamic" module so that we can use the fancy `this` rebinding. Otherwise we have to use
// The old school `context.commit` and `context.dispatch` style syntax.
@Module({ namespaced: true, name: StoreType.demoWalkthrough })
export class DemoWalkthroughStore extends VuexModule<ThisType<DemoWalkthroughState>, RootState>
  implements DemoWalkthroughState {
  public currentTooltip: number = initialState.currentTooltip;
  public tooltips: DemoTooltip[] = initialState.tooltips;
  public tooltipsLoaded: boolean = initialState.tooltipsLoaded;

  get currentCyTooltips(): DemoTooltip[] {
    return this.tooltips.filter(t => t.visible && t.type == TooltipType.CyTooltip);
  }

  get currentHtmlTooltips(): DemoTooltip[] {
    return this.tooltips.filter(t => t.visible && t.type == TooltipType.HTMLTooltip);
  }

  get areTooltipsLoaded(): boolean {
    return this.tooltipsLoaded;
  }

  @Mutation
  public setCurrentTooltips(tooltips: DemoTooltip[]) {
    if (tooltips.length > 0) {
      tooltips[this.currentTooltip].visible = true;
    }
    this.tooltipsLoaded = false;
    this.tooltips = tooltips;
  }

  @Mutation
  public resetState() {
    resetStoreState(this, baseState);
  }

  @Mutation
  public loadCyTooltips(cy: cytoscape.Core) {
    if (this.tooltipsLoaded) {
      return;
    }

    const tooltips = [...this.tooltips];

    for (let i = 0; i < tooltips.length; i++) {
      const t = tooltips[i];
      if (t.type !== TooltipType.CyTooltip) {
        continue;
      }

      const pos = cy.getElementById(t.target).position();
      if (pos) {
        tooltips[i].config = {
          ...tooltips[i].config,
          ...pos
        };
      }
    }

    this.tooltipsLoaded = true;
    this.tooltips = tooltips;
  }

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

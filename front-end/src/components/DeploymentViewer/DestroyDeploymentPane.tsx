import Vue, { CreateElement, VNode } from 'vue';
import Component from 'vue-class-component';
import { namespace } from 'vuex-class';
import Loading from '@/components/Common/Loading.vue';
import { LoadingContainerProps } from '@/types/component-types';

const deployment = namespace('deployment');

@Component
export default class DestroyDeploymentPane extends Vue {
  @deployment.Action destroyDeployment!: () => void;
  @deployment.State isDestroyingDeployment!: boolean;

  public render(h: CreateElement): VNode {
    const loadingProps: LoadingContainerProps = {
      show: this.isDestroyingDeployment,
      label: 'Tearing down deployment, please wait...'
    };

    return (
      <Loading props={loadingProps}>
        <b-list-group class="destroy-deployment-pane-container mb-2 mt-2 mr-2 ml-2">
          <h4>
            Are you sure you want to destroy this deployment?
            <br />
            <br />
            This change is permanent!
          </h4>
          <b-button variant="danger" class="mt-2" on={{ click: this.destroyDeployment }}>
            Destroy Deployment
          </b-button>
        </b-list-group>
      </Loading>
    );
  }
}

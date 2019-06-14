import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';

@Component
export default class ProjectSettings extends Vue {
  public render(h: CreateElement): VNode {
    return (
      <div class="content-wrapper">
        <div class="content-heading display-flex">
          <div class="layout--constrain flex-grow--1">
            <div>Project Settings
              <small>The settings for this project.</small>
            </div>
          </div>
        </div>
        <div class="layout--constrain">
          <div class="row justify-content-lg-center">
            <div class="col-lg-8 align-self-center">
              <div class="card card-default">
                <div class="card-header">
                  Projects
                </div>

                <div class="card-footer">
                  test
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }
}

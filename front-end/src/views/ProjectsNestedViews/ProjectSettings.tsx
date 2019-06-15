import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import {ProjectConfig, ProjectLogLevel} from "@/types/graph";
import {namespace} from "vuex-class";

const project = namespace('project');

@Component
export default class ProjectSettings extends Vue {
  @project.State openedProjectConfig!: ProjectConfig | null;

  @project.Action setProjectConfigLoggingLevel!: (projectConfigLoggingLevel: ProjectLogLevel) => void;

  private getLogLevelValue() {
    if (!this.openedProjectConfig || !this.openedProjectConfig.logging || !this.openedProjectConfig.logging.level) {
      return ProjectLogLevel.LOG_ALL;
    }
    return this.openedProjectConfig.logging.level;
  }

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
                  Project Settings
                </div>
                <div class="card-body text-align--left">
                  <b-form-group
                    description="The logging level to use when Code Blocks run in production. Note that changing this level requires a re-deploy to take effect!">
                    <label class="d-block" htmlFor="logging-level-input-select">
                      Logging Level
                    </label>
                    <div class="input-group with-focus">
                      <b-form-select
                        id="logging-level-input-select"
                        /* Maybe Free won't notice this, I'm not sure what I'm supposed to do instead. */
                        value={this.getLogLevelValue()}
                        on={{change: this.setProjectConfigLoggingLevel}}
                      >
                        <option value={ProjectLogLevel.LOG_ALL}>Log all executions</option>
                        <option value={ProjectLogLevel.LOG_ERRORS}>Log only errors</option>
                        <option value={ProjectLogLevel.LOG_NONE}>No logging</option>
                      </b-form-select>
                    </div>
                  </b-form-group>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }
}

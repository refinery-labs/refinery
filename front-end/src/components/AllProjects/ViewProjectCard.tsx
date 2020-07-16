import { Component, Prop, Vue } from 'vue-property-decorator';
import { SearchSavedProjectsResult } from '@/types/api-types';
import { namespace } from 'vuex-class';
import { linkFormatterUtils } from '@/constants/router-constants';
import { LoadingContainerProps } from '@/types/component-types';
import Loading from '@/components/Common/Loading.vue';
import { getFriendlyDurationSinceString } from '@/utils/time-utils';
import { loadMoreProjectVersionsOptionValue } from '@/constants/project-editor-constants';

const allProjects = namespace('allProjects');

export interface ViewProjectCardProps {
  project: SearchSavedProjectsResult;
  selectedVersion: number;
  isLoadingMoreProjects: boolean;
  onSelectedVersionChanged: (version: number) => void;
}

@Component
export default class ViewProjectCard extends Vue implements ViewProjectCardProps {
  @allProjects.State renameProjectId!: string | null;
  @allProjects.State renameProjectInput!: string | null;
  @allProjects.State renameProjectBusy!: boolean;
  @allProjects.State renameProjectError!: string | null;
  @allProjects.Mutation setRenameProjectInput!: (text: string) => void;

  @allProjects.Action startDeleteProject!: (project: SearchSavedProjectsResult) => void;
  @allProjects.Action renameProject!: (id: string) => void;

  @Prop() project!: SearchSavedProjectsResult;
  @Prop() selectedVersion!: number;
  @Prop() isLoadingMoreProjects!: boolean;

  @Prop() onSelectedVersionChanged!: (version: number) => void;

  public getProjectShareLink() {
    // If the latest version is selected, then don't add the version to the generated URL
    if (!this.project.versions[0] || this.selectedVersion === this.project.versions[0].version) {
      return linkFormatterUtils.viewProjectFormatter(this.project.id);
    }

    return linkFormatterUtils.viewProjectFormatter(this.project.id, this.selectedVersion);
  }

  public renderProjectName(project: SearchSavedProjectsResult) {
    if (project.id === this.renameProjectId) {
      return (
        <div>
          <b-input
            class="w-100 flex-grow--1"
            type="text"
            placeholder="Name of project"
            autofocus={true}
            value={this.renameProjectInput}
            on={{ change: this.setRenameProjectInput }}
          />

          <b-form-invalid-feedback state={!this.renameProjectError}>{this.renameProjectError}</b-form-invalid-feedback>
        </div>
      );
    }

    return <h4 class="m-0">{project.name}</h4>;
  }

  renderVersionSelect() {
    if (this.project.versions.length === 1) {
      return null;
    }

    const latestVersion = this.project.versions[0];
    const otherVersions = this.project.versions.slice(1);

    const totalVersions = this.project.total_versions;
    const hasMoreVersionsAvailable = totalVersions === undefined || this.project.versions.length !== totalVersions;

    return (
      <b-form-select
        class="width--auto min-width--200px"
        // Setting the key forces a reload of the element when more elements load in. This prevents "sticking" to "load more" in the list.
        key={this.project.versions.length}
        value={this.selectedVersion}
        on={{ change: this.onSelectedVersionChanged }}
      >
        <option value={latestVersion.version}>
          Latest - {getFriendlyDurationSinceString(latestVersion.timestamp * 1000)}
        </option>
        {otherVersions.map(({ version, timestamp }) => (
          <option value={version}>
            v{version} - {getFriendlyDurationSinceString(timestamp * 1000)}
          </option>
        ))}
        {hasMoreVersionsAvailable ? (
          <option value={loadMoreProjectVersionsOptionValue}>Load more versions...</option>
        ) : null}
      </b-form-select>
    );
  }

  public renderDeployedStatusMessage() {
    if (!this.project.deployment) {
      return <div />;
    }

    return (
      <div>
        <i class="fas fa-cloud-upload-alt" /> Deployed
      </div>
    );
  }

  public render() {
    const project = this.project;

    const durationSinceUpdated = getFriendlyDurationSinceString(project.timestamp * 1000);

    const disableRenameButton = this.renameProjectId !== null && this.renameProjectId !== project.id;

    const viewProjectLink = this.getProjectShareLink();

    const renameIconClasses = {
      fas: true,
      'fa-edit': this.renameProjectId !== project.id,
      'fa-check': this.renameProjectId === project.id
    };

    const loadingText = this.isLoadingMoreProjects ? 'Loading project versions...' : 'Renaming...';
    const isRenamingProject = this.renameProjectBusy && this.renameProjectId === project.id;

    const loadingProps: LoadingContainerProps = {
      label: loadingText,
      show: isRenamingProject || this.isLoadingMoreProjects
    };

    return (
      <Loading props={loadingProps}>
        <div class="media align-items-center">
          <div class="media-body d-flex">
            <div class="flex-grow--1 mr-2">
              {this.renderProjectName(project)}

              <small class="text-muted">Created {durationSinceUpdated}</small>

              {this.renderDeployedStatusMessage()}

              <div class="text-align--right">{this.renderVersionSelect()}</div>
              {/*<p>*/}
              {/*  If I had a description, this is where I would put it! Thanks, Mandatory. This is why we can't have*/}
              {/*  nice things.*/}
              {/* I appologize for nothing! -mandatory */}
              {/*</p>*/}
            </div>
            <div class="ml-auto d-flex flex-direction--column">
              <div class="flex-grow--1 d-flex w-100 mb-2">
                <b-button
                  class="mr-2"
                  variant="info"
                  on={{ click: () => this.renameProject(project.id) }}
                  disabled={disableRenameButton}
                >
                  Rename <span class={renameIconClasses} />
                </b-button>

                <b-button class="" variant="danger" on={{ click: () => this.startDeleteProject(project) }}>
                  Delete <span class="fas fa-trash" />
                </b-button>
              </div>
              <div class="flex-grow--1 w-100">
                <b-button class="w-100" variant="primary" to={viewProjectLink}>
                  Open in Editor <span class="fas fa-code" />
                </b-button>
              </div>
            </div>
          </div>
        </div>
      </Loading>
    );
  }
}

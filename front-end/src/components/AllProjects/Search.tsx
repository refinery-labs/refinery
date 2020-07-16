import { CreateElement, VNode } from 'vue';
import { Component, Vue } from 'vue-property-decorator';
import ContentWrapper from '@/components/Layout/ContentWrapper.vue';
import { SearchSavedProjectsResult } from '@/types/api-types';
import { namespace } from 'vuex-class';
import CardToolTsx from '@/components/Common/CardToolTsx';
import { preventDefaultWrapper } from '@/utils/dom-utils';
import ViewProjectCard, { ViewProjectCardProps } from '@/components/AllProjects/ViewProjectCard';
import { ProjectCardStateLookup, SelectProjectVersion } from '@/types/all-project-types';
import { loadMoreProjectVersionsOptionValue } from '@/constants/project-editor-constants';

const allProjects = namespace('allProjects');

@Component({
  components: { ContentWrapper }
})
export default class Search extends Vue {
  private loadingMoreProjectsForProjectWithId: null | string = null;

  @allProjects.State availableProjects!: SearchSavedProjectsResult[];
  @allProjects.State isSearching!: Boolean;
  @allProjects.State searchBoxText!: string;

  @allProjects.State cardStateByProjectId!: ProjectCardStateLookup;

  @allProjects.State deleteModalVisible!: boolean;
  @allProjects.State deleteProjectId!: string | null;
  @allProjects.State deleteProjectName!: string | null;

  @allProjects.State newProjectInput!: string | null;
  @allProjects.State newProjectErrorMessage!: string | null;
  @allProjects.Getter newProjectInputValid!: boolean;
  @allProjects.Mutation setNewProjectInput!: (text: string) => void;

  @allProjects.State uploadProjectInput!: string | null;
  @allProjects.State uploadProjectErrorMessage!: string | null;
  @allProjects.Getter uploadProjectInputValid!: boolean;
  @allProjects.Mutation setUploadProjectInput!: (text: string) => void;
  @allProjects.Action getUploadFileContents!: (e: Event) => void;

  @allProjects.State importProjectInput!: string | null;
  @allProjects.State importProjectErrorMessage!: string | null;
  @allProjects.Getter importProjectInputValid!: boolean;
  @allProjects.Mutation setImportProjectInput!: (text: string) => void;

  @allProjects.Mutation setSearchBoxInput!: (text: string) => void;
  @allProjects.Mutation setDeleteModalVisibility!: (val: boolean) => void;
  @allProjects.Mutation setCardSelectedVersion!: (params: SelectProjectVersion) => void;

  @allProjects.Action performSearch!: (e: string) => {};
  @allProjects.Action getAllProjectVersions!: (e: string) => {};
  @allProjects.Action createProject!: () => void;
  @allProjects.Action uploadProject!: () => void;
  @allProjects.Action importProject!: () => void;
  @allProjects.Action deleteProject!: () => void;

  onSearchClicked(e: Event) {
    if (!e || !e.target) {
      return;
    }

    e.preventDefault();
    // This is certainly annoying
    this.performSearch((e.target as HTMLInputElement).value);
  }

  public mounted() {
    this.performSearch('');
  }

  public renderCardTool() {
    // This is frustrating with Vue props and Typescript... Let's just shim it for now.
    return (
      // @ts-ignore
      <CardToolTsx
        props={{
          refresh: true,
          onRefresh: this.performSearch,
          forceSpin: this.isSearching
        }}
      />
    );
  }

  public renderPaginationTable() {
    if (this.availableProjects.length === 0) {
      return null;
    }

    return (
      <ul class="pagination pagination-sm">
        <li class="page-item active">
          <a class="page-link" href="#">
            1
          </a>
        </li>
        {/*TODO: Add Pagination support*/}
        {/*<li class="page-item">*/}
        {/*<a class="page-link" href="#">2</a>*/}
        {/*</li>*/}
        {/*<li class="page-item">*/}
        {/*<a class="page-link" href="#">3</a>*/}
        {/*</li>*/}
        {/*<li class="page-item">*/}
        {/*<a class="page-link" href="#">»</a>*/}
        {/*</li>*/}
      </ul>
    );
  }

  public renderCreateProjectCard() {
    const createProjectErrorMessage = this.newProjectErrorMessage || 'Must provide name for new project!';
    return (
      <b-card class="card-default" header="Create New Project">
        <b-form on={{ submit: preventDefaultWrapper(this.createProject) }}>
          <b-form-group
            id="new-project-input-group"
            label="Project Name:"
            label-for="new-project-input"
            description="This will be the name of the project you will create."
          >
            <b-input
              id="new-project-input"
              class="mb-2 mr-sm-2 mb-sm-0"
              required={true}
              state={this.newProjectInput !== null ? this.newProjectInputValid : null}
              value={this.newProjectInput}
              on={{ change: this.setNewProjectInput }}
              placeholder="eg, Personal Website"
            />
          </b-form-group>

          <b-button variant="primary" type="submit">
            Create Project
          </b-button>
          <b-form-invalid-feedback state={this.newProjectErrorMessage === null && this.newProjectInputValid}>
            {createProjectErrorMessage}
          </b-form-invalid-feedback>
        </b-form>
      </b-card>
    );
  }

  public renderUploadProjectCard() {
    const uploadProjectErrorMessage = this.uploadProjectErrorMessage || 'Invalid JSON supplied.';

    const state = this.uploadProjectInput !== null ? this.uploadProjectInputValid : null;

    return (
      <b-card class="card-default" header="Upload Project From File">
        <b-form on={{ submit: preventDefaultWrapper(this.uploadProject) }}>
          <b-form-group
            id="import-project-input-group"
            label="Select JSON File:"
            label-for="import-project-input"
            description="This is a file that you had previously exported, most likely."
          >
            <b-form-file
              id="import-project-input"
              class="mb-2 mr-sm-2 mb-sm-0"
              accept=".json"
              required={true}
              state={state}
              on={{ change: this.getUploadFileContents }}
              placeholder="eg, my-amazing-project.json"
            />
          </b-form-group>

          <b-button variant="primary" type="submit">
            Upload Project
          </b-button>
          <b-form-invalid-feedback state={this.uploadProjectErrorMessage === null && state}>
            {uploadProjectErrorMessage}
          </b-form-invalid-feedback>
        </b-form>
      </b-card>
    );
  }

  public renderImportProjectCard() {
    const importProjectErrorMessage = this.importProjectErrorMessage || 'Invalid JSON supplied.';
    const state = this.importProjectInput !== null ? this.importProjectInputValid : null;

    return (
      <b-card class="card-default" header="Import Project From Text">
        <b-form on={{ submit: preventDefaultWrapper(this.importProject) }}>
          <b-form-group
            id="import-project-text-input-group"
            label="JSON Form Input:"
            label-for="import-project-text-input"
          >
            <b-form-textarea
              id="import-project-text-input"
              size="sm"
              class="padding-bottom--normal-small"
              required={true}
              state={state}
              value={this.importProjectInput}
              on={{ change: this.setImportProjectInput }}
              placeholder={'You may paste project exported JSON here. Eg,\n{"some-json":"value"}'}
            />
          </b-form-group>

          <b-button variant="primary" type="submit">
            Import Project
          </b-button>
          <b-form-invalid-feedback state={this.importProjectErrorMessage === null && state}>
            {importProjectErrorMessage}
          </b-form-invalid-feedback>
        </b-form>
      </b-card>
    );
  }

  public renderProjectCard(project: SearchSavedProjectsResult) {
    const cardState = this.cardStateByProjectId[project.id];

    if (!cardState) {
      throw new Error('Card state not found in store');
    }

    const cardProps: ViewProjectCardProps = {
      project: project,
      selectedVersion: cardState.selectedVersion,
      isLoadingMoreProjects: this.loadingMoreProjectsForProjectWithId === project.id,
      onSelectedVersionChanged: async (version: number) => {
        const loadMoreVersions = version === loadMoreProjectVersionsOptionValue;

        if (loadMoreVersions) {
          this.loadingMoreProjectsForProjectWithId = project.id;
          await this.getAllProjectVersions(project.id);
          this.loadingMoreProjectsForProjectWithId = null;
        }

        const versionToSelect = loadMoreVersions ? project.versions[0].version : version;

        this.setCardSelectedVersion({
          projectId: project.id,
          selectedVersion: versionToSelect
        });
      }
    };

    return <ViewProjectCard props={cardProps} />;
  }

  public renderSearchTable() {
    const availableProjects = this.availableProjects;

    // TODO: Add Pagination support
    const chunked = availableProjects; //.slice().slice(0, 10);

    // One row for every project displayed
    const projectEntries = chunked.map(project => {
      return (
        <tr>
          <td>{this.renderProjectCard(project)}</td>
        </tr>
      );
    });

    const headerTitle = availableProjects.length === 0 ? 'No projects found!' : 'Description';

    return (
      <b-card class="card-default" no-body>
        <b-card-header>
          {this.renderCardTool()}
          Existing Projects
        </b-card-header>
        <div class="table-responsive">
          <table class="table table-striped table-bordered table-hover">
            <thead>
              <tr>
                <th>{headerTitle}</th>
              </tr>
            </thead>
            <tbody>{projectEntries}</tbody>
          </table>
        </div>
        <b-card-footer class="d-flex">
          {/*<button class="btn btn-sm btn-secondary">Clear</button>*/}
          <nav class="ml-auto">{this.renderPaginationTable()}</nav>
        </b-card-footer>
      </b-card>
    );
  }

  public renderDeleteProjectModal() {
    const modalOnHandlers = {
      hidden: () => this.setDeleteModalVisibility(false),
      ok: () => this.setDeleteModalVisibility(false)
    };

    return (
      <b-modal
        on={modalOnHandlers}
        ref="my-modal"
        hide-footer
        title="Delete Project Confirmation"
        visible={this.deleteModalVisible}
      >
        <div class="d-block text-center">
          <h3>Are you sure that you want to delete this project?</h3>
          <br />
          <h2>{this.deleteProjectName}</h2>
          <br />
          <h3 style="color: red">This change is permanent!</h3>
        </div>
        <b-button class="mt-3" variant="outline-danger" block on={{ click: this.deleteProject }}>
          Delete Project
        </b-button>
        <b-button class="mt-2" variant="primary" block on={{ click: () => this.setDeleteModalVisibility(false) }}>
          Cancel
        </b-button>
      </b-modal>
    );
  }

  public renderCardSearch() {
    return (
      <b-card class="card-default" header="Find Project">
        <b-form on={{ submit: this.onSearchClicked }}>
          <b-form-group
            id="new-project-input-group"
            label="By Project Name:"
            label-for="new-project-input"
            description="If a project name contains this text, it will be shown in the search results."
          >
            <b-input
              class="form-control mb-2"
              type="text"
              placeholder="Search projects by name..."
              value={this.searchBoxText}
              on={{ change: this.setSearchBoxInput }}
            />
          </b-form-group>

          <b-button variant="secondary" size="lg" type="submit">
            Search
          </b-button>
        </b-form>
      </b-card>
    );
  }

  public render(h: CreateElement): VNode {
    return (
      <ContentWrapper>
        <div class="content-heading display-flex">
          <div class="layout--constrain flex-grow--1">
            <div>
              All Projects
              <small>Search for all of your projects</small>
            </div>
          </div>
        </div>
        <div class="layout--constrain">
          <b-row>
            <b-col md={4}>{this.renderCreateProjectCard()}</b-col>
            <b-col md={4}>{this.renderUploadProjectCard()}</b-col>
            <b-col md={4}>{this.renderImportProjectCard()}</b-col>
          </b-row>
          <b-row>
            <b-col md={9}>{this.renderSearchTable()}</b-col>

            <b-col md={3}>{this.renderCardSearch()}</b-col>
          </b-row>
        </div>

        {this.renderDeleteProjectModal()}
      </ContentWrapper>
    );
  }
}

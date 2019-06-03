import {CreateElement, VNode} from 'vue';
import {Component, Prop, Vue} from 'vue-property-decorator';
import moment from 'moment';
import ContentWrapper from '@/components/Layout/ContentWrapper.vue';
import {SearchSavedProjectsResult} from '@/types/api-types';
import {namespace} from 'vuex-class';
import CardToolTsx from '@/components/Common/CardToolTsx';
import {linkFormatterUtils} from '@/constants/router-constants';

const allProjects = namespace('allProjects');

@Component({
  components: {ContentWrapper}
})
export default class Search extends Vue {
  @allProjects.State availableProjects!: SearchSavedProjectsResult[];
  @allProjects.State isSearching!: Boolean;
  @allProjects.State searchBoxText!: string;
  
  @allProjects.State deleteModalVisible!: boolean;
  @allProjects.State deleteProjectId!: string | null;
  @allProjects.State deleteProjectName!: string | null;
  
  @allProjects.State newProjectInput!: string;
  @allProjects.State newProjectInputValid!: boolean | null;
  @allProjects.State newProjectErrorMessage!: string | null;
  
  @allProjects.Mutation setSearchBoxInput!: (text: string) => void;
  @allProjects.Mutation setNewProjectInput!: (text: string) => void;
  @allProjects.Mutation setDeleteModalVisibility!: (val: boolean) => void;
  
  @allProjects.Action performSearch!: () => {};
  @allProjects.Action createProject!: () => void;
  @allProjects.Action startDeleteProject!: (project: SearchSavedProjectsResult) => void;
  @allProjects.Action deleteProject!: () => void;
  
  onCreateProjectSubmit(e: Event) {
    e.preventDefault();
    this.createProject();
  }
  
  onSearchClicked(e: Event) {
    if (!e || !e.target) {
      return;
    }
    
    // This is certainly annoying
    this.setSearchBoxInput((e.target as HTMLInputElement).value)
  }
  
  public mounted() {
    this.performSearch();
  }
  
  public renderCardTool() {
    // This is frustrating with Vue props and Typescript... Let's just shim it for now.
    return (
      // @ts-ignore
      <CardToolTsx props={{
        refresh: true,
        onRefresh: this.performSearch,
        forceSpin: this.isSearching
      }} />
    );
  }
  
  public renderPaginationTable() {
    if (this.availableProjects.length === 0) {
      return null;
    }
    
    return (
      <ul class="pagination pagination-sm">
        {/*<li class="page-item active">*/}
          {/*<a class="page-link" href="#">1</a>*/}
        {/*</li>*/}
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
  
  public renderSearchTable() {
    const availableProjects = this.availableProjects;
    
    // TODO: Add Pagination support
    const chunked = availableProjects; //.slice().slice(0, 10);
    
    const headerTitle = availableProjects.length === 0 ? 'No projects found!' : 'Description';
    
    const createProjectErrorMessage = this.newProjectErrorMessage || 'Must provide name for new project!';
    
    return (
      <div class="col-lg-9">
        <div class="card card-default">
          <div class="card-header">
            {this.renderCardTool()}
            Projects
          </div>
          <div class="table-responsive">
            <table class="table table-striped table-bordered table-hover">
              <thead>
              <tr>
                <th>{headerTitle}</th>
              </tr>
              </thead>
              <tbody>
              {chunked.map(project => this.renderSearchResult(project))}
              </tbody>
            </table>
          </div>
          <div class="card-footer">
            <div class="d-flex">
              {/*<button class="btn btn-sm btn-secondary">Clear</button>*/}
              <nav class="ml-auto">
                {this.renderPaginationTable()}
              </nav>
              <b-form inline on={{submit: this.onCreateProjectSubmit}}>
                <label class="mr-sm-2" for="new-project-input">Project Name</label>
                <b-input
                  id="new-project-input"
                  class="mb-2 mr-sm-2 mb-sm-0"
                  state={this.newProjectInputValid}
                  on={{change: this.setNewProjectInput}}
                  placeholder="eg, Personal Website" />
                <b-button variant="primary" type="submit">Create Project</b-button>
                <b-form-invalid-feedback state={this.newProjectErrorMessage === null && this.newProjectInputValid}>
                  {createProjectErrorMessage}
                </b-form-invalid-feedback>
              </b-form>
            </div>
          </div>
        </div>
      </div>
    );
  }
  
  public renderSearchResult(project: SearchSavedProjectsResult) {
    const updatedTime = moment(project.timestamp * 1000);
    const durationSinceUpdated = moment.duration(-moment().diff(updatedTime)).humanize(true);
  
    const viewProjectLink = linkFormatterUtils.viewProjectFormatter(project.id);
    
    return (
      <tr>
        <td>
          <div class="media align-items-center">
            <div class="media-body d-flex">
              <div>
                <h4 class="m-0">{project.name}</h4>
                <small class="text-muted">Last updated {durationSinceUpdated}</small>
                <p>If I had a description, this is where I would put it! Thanks, Mandatory. This is why we can't have nice things.</p>
              </div>
              <div class="ml-auto">
                <b-button variant="danger" on={{click: () => this.startDeleteProject(project)}}>
                  <span class="fas fa-trash" />
                </b-button>
              </div>
              <div style={{'margin-left': '8px'}}>
                <b-button variant="primary" to={viewProjectLink}>View</b-button>
              </div>
            </div>
          </div>
        </td>
      </tr>
    );
  }
  
  public render(h: CreateElement): VNode {
    return (
      <ContentWrapper>
        <div class="content-heading display-flex">
          <div class="layout--constrain flex-grow--1">
            <div>All Projects
              <small>Search for all of your projects</small>
            </div>
          </div>
        </div>
        <div class="layout--constrain">
          <div class="row">
            {this.renderSearchTable()}
            
            <div class="col-lg-3">
              <h3 class="m-0 pb-3">Filters</h3>
              <div class="form-group mb-4">
                <label class="col-form-label mb-2">By Name</label>
                <br/>
                <input class="form-control mb-2" type="text" placeholder="Search projects by name..."
                       value={this.searchBoxText}
                       on={{change: this.onSearchClicked}} />
              </div>
              <button class="btn btn-secondary btn-lg"
                      on={{click: this.performSearch}}>Search</button>
            </div>
          </div>
        </div>
        
        <b-modal ref="my-modal" hide-footer title="Delete Project Confirmation" visible={this.deleteModalVisible}>
          <div class="d-block text-center">
            <h3>Are you sure that you want to delete this project?</h3>
            <br/>
            <h2>{this.deleteProjectName}</h2>
            <br/>
            <h3 style="color: red">This change is permanent!</h3>
          </div>
          <b-button class="mt-3" variant="outline-danger" block
                    on={{click: this.deleteProject}}>
            Delete Project
          </b-button>
          <b-button class="mt-2" variant="primary" block on={{click: () => this.setDeleteModalVisibility(false)}}>
            Cancel
          </b-button>
        </b-modal>
      </ContentWrapper>
    );
  }
}

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
  
  @allProjects.Action performSearch!: () => {};
  
  @allProjects.Mutation setSearchBoxInput!: (text: string) => {};
  
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
        <li class="page-item active">
          <a class="page-link" href="#">1</a>
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
  
  public renderSearchTable() {
    const availableProjects = this.availableProjects;
    
    // TODO: Add Pagination support
    const chunked = availableProjects; //.slice().slice(0, 10);
    
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
                <th>Description</th>
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
                <router-link class="btn btn-info btn-sm" to={viewProjectLink}>View</router-link>
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
      </ContentWrapper>
    );
  }
}

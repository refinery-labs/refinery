import {CreateElement, VNode} from 'vue';
import {Component, Prop, Vue} from 'vue-property-decorator';
import moment from 'moment';
import CardTool from '@/components/Common/CardTool.vue';
import ContentWrapper from '@/components/Layout/ContentWrapper.vue';
import {ProjectSearchResult} from '@/types/api-types';
import {namespace} from 'vuex-class';
import CardToolTsx from '@/components/Common/CardToolTsx';

const allProjects = namespace('allProjects');

@Component({
  components: {ContentWrapper}
})
export default class Search2 extends Vue {
  @allProjects.State availableProjects!: ProjectSearchResult[];
  @allProjects.State isSearching!: Boolean;
  
  @allProjects.Action performSearch!: () => {};
  
  public mounted() {
    this.performSearch();
  }
  
  public renderCardTool() {
    // This is frustrating with Vue props and Typescript... Let's just shim it for now.
    return (
      // @ts-ignore
      <CardToolTsx props={{
        refresh: true,
        forceSpin: this.isSearching
      }} />
    );
  }
  
  renderSearchTable() {
    const availableProjects = this.availableProjects;
    
    const chunked = availableProjects.slice().slice(0, 10);
    
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
                <ul class="pagination pagination-sm">
                  <li class="page-item active">
                    <a class="page-link" href="#">1</a>
                  </li>
                  <li class="page-item">
                    <a class="page-link" href="#">2</a>
                  </li>
                  <li class="page-item">
                    <a class="page-link" href="#">3</a>
                  </li>
                  <li class="page-item">
                    <a class="page-link" href="#">»</a>
                  </li>
                </ul>
              </nav>
            </div>
          </div>
        </div>
      </div>
    );
  }
  
  public renderSearchResult(project: ProjectSearchResult) {
    const updatedTime = moment(project.timestamp * 1000);
    const durationSinceUpdated = moment.duration(-moment().diff(updatedTime)).humanize(true);
  
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
                <div class="btn btn-info btn-sm">View</div>
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
                <input class="form-control mb-2" type="text" placeholder="Search projects by name..."/>
              </div>
              <button class="btn btn-secondary btn-lg">Search</button>
            </div>
          </div>
        </div>
      </ContentWrapper>
    );
  }
}

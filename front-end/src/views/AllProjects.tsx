import Vue, {CreateElement, VNode} from 'vue';
import Component from 'vue-class-component';
import {namespace, State} from 'vuex-class';
import moment from 'moment';
import {ProjectSearchResult} from '@/types/api-types';

const allProjects = namespace('allProjects');

@Component
export default class AllProjects extends Vue {
  @allProjects.State availableProjects!: ProjectSearchResult[];
  
  private openProject(projectId: string) {
  
  }
  
  public renderTableSlots() {
    return {
      versions: (element: Element) => <div></div>
    };
  }
  
  public renderCard(project: ProjectSearchResult) {
    const updatedTime = moment(project.timestamp * 1000);
    const durationSinceUpdated = moment.duration(-moment().diff(updatedTime));
    
    const datetime = new Date(project.timestamp * 1000);
    
    const sortedVersions = project.versions.slice().sort().reverse();
   
    
    return (
      <b-card no-body class="card card-default text-align--left">
        <b-card-header class="display--flex">
          <div class="flex-grow--1">{project.name}</div>
          <div class="btn btn-info btn-sm">View</div>
        </b-card-header>
        {/*<b-card-body>*/}
          {/*<b-card-sub-title className="mb-2">This is a description</b-card-sub-title>*/}
        {/*</b-card-body>*/}
        <b-card-footer>
          <div class="text-sm text-muted">
            {`Last updated ${durationSinceUpdated.humanize(true)}`}
          </div>
        </b-card-footer>
      </b-card>
    );
    
    return (
      <b-card>
        <b-card-header>{project.name}</b-card-header>
        <b-card-text>
          {`Last Deployed: ${datetime.toLocaleTimeString()}, ${datetime.toLocaleDateString()}`}
        </b-card-text>
        <b-button href="#" variant="primary">Open Project</b-button>
      </b-card>
    );
    
    return (
      <b-jumbotron header-level="4" class="text-align--left">
      
        <template slot="header">
          Bootstrap Vue
        </template>
        <template slot="lead">
          This is a simple hero unit, a simple jumbotron-style component for
          calling extra attention to featured content or information.
        </template>
        <hr className="my-4"/>
        <p>
          It uses utility classes for typography and spacing to space content
          out within the larger container.
        </p>
        <b-btn variant="primary" className="mr-1" href="#">Do Something</b-btn>
        <b-btn variant="success" href="#">Do Something Else</b-btn>
      </b-jumbotron>
    );
    
    return (
      <b-card
        no-body>
  
        <b-card-body>
          <b-card-title></b-card-title>
          <b-card-sub-title className="mb-2">
          
          </b-card-sub-title>
        </b-card-body>
        
        <b-card-footer>
          <b-row>
            <b-col cols="2">
              <label>Version:</label>
            </b-col>
            <b-col cols="6">
              <b-form-select options={project.versions} required value={sortedVersions && sortedVersions[0]} />
            </b-col>
            <b-col cols="4">
              <b-link href="#" className="card-link">Another link</b-link>
            </b-col>
          </b-row>
        </b-card-footer>
      </b-card>
    );
  }

  public render(h: CreateElement): VNode {
    const fields = ['name', 'versions', 'open_project'];
    
    if (!this.availableProjects) {
      return (
        <h2>Please create a new project!</h2>
      );
    }
    
    return (
      <div class="all-projects-page">
        <h2>All Projects</h2>
        <b-container class="mt-6">
          <b-card-group columns>
            {this.availableProjects.map(project => this.renderCard(project))}
          </b-card-group>
        </b-container>
      </div>
    );
  }
}
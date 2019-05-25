/**
 * Setting store to control layout behavior
 */
import {Module} from 'vuex';
import {RootState, AllProjectsState} from '@/store/store-types';

const initialState = [{
  "timestamp": 1554179683,
  "versions": [1],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "New Project"
}, {
  "timestamp": 1554179683,
  "versions": [1],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "New Project"
}, {
  "timestamp": 1554179683,
  "versions": [1],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "New Project"
}, {
  "timestamp": 1554179683,
  "versions": [1,2,3,4],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "New Project"
}, {
  "timestamp": 1554179683,
  "versions": [1],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "New Project"
}, {
  "timestamp": 1554179683,
  "versions": [1,2],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "New Project"
}, {
  "timestamp": 1554179683,
  "versions": [1],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "New Project"
}, {
  "timestamp": 1554179683,
  "versions": [1],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "New Project"
}, {
  "timestamp": 1554179683,
  "versions": [1],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "New Project"
}, {
  "timestamp": 1554179683,
  "versions": [1],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "New Project"
}];

const moduleState: AllProjectsState = {
  availableProjects: initialState,
  searchBox: '',
  isSearching: false
};

const AllProjectsModule: Module<AllProjectsState, RootState> = {
  namespaced: true,
  state: moduleState,
  getters: {},
  mutations: {},
  actions: {}
};

export default AllProjectsModule;

/**
 * Setting store to control layout behavior
 */
import {Module} from 'vuex';
import {RootState, AllProjectsState} from '@/store/store-types';

const initialState = [{
  "timestamp": 1554179683,
  "versions": [1],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "World Dominator"
}, {
  "timestamp": 1554179683,
  "versions": [1],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "Secret VC Backdoor Agent"
}, {
  "timestamp": 1554179683,
  "versions": [1],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "Friendship Compliance Tool"
}, {
  "timestamp": 1558816788,
  "versions": [1,2,3,4],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "Weekly Texting Metrics"
}, {
  "timestamp": 1554179683,
  "versions": [1],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "Twitter Feed Reader"
}, {
  "timestamp": 1554179683,
  "versions": [1,2],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "New Project"
}, {
  "timestamp": 1554179683,
  "versions": [1],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "Spooky Scary Skeleton Generator"
}, {
  "timestamp": 1554179683,
  "versions": [1],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "Spooky Scary Skeleton Generator (v2)"
}, {
  "timestamp": 1554179683,
  "versions": [1],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "Twitter Feed Reader -- Modern Version!"
}, {
  "timestamp": 1554179683,
  "versions": [1],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "New Project for The President Himself Number Two"
}, {
  "timestamp": 1554179683,
  "versions": [1],
  "id": "bee8d465-61a9-4295-aadc-4d2f006dd128",
  "name": "New Project for The President Himself"
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
  mutations: {
    setSearchingStatus(state, isSearching) {
      state.isSearching = isSearching;
    }
  },
  actions: {
    async performSearch(context) {
      context.commit('setSearchingStatus', true);
      // TODO: Make this make an AJAX request
  
      setTimeout(() => {
        context.commit('setSearchingStatus', false);
      }, 3000);
    }
  }
};

export default AllProjectsModule;

import { Route } from 'vue-router';
import store from '@/store';
import { UserMutators } from '@/constants/store-constants';

export async function guardLoggedIn(to: Route, from: Route, next: Function) {
  if (store.state.user.authenticated) {
    // allow to enter route
    next();
    return;
  }

  await store.dispatch(`user/fetchAuthenticationState`);

  // We haven't any login data, so go fetch it and keep going...
  if (store.state.user.authenticated) {
    // allow to enter route
    next();
    return;
  }

  // Throw the data into the store for later redirect usage
  store.commit(`user/${UserMutators.setRedirectState}`, to.fullPath);

  // go to '/login';
  next('/login');
}

import { Module } from 'vuex';
import validator from 'validator';
import phone from 'phone';
import uuid from 'uuid/v4';
import router from '../../router';
import { RootState, UserState } from '@/store/store-types';
import { ProjectViewMutators, UserActions, UserMutators } from '@/constants/store-constants';
import {
  GetAuthenticationStatusResponse,
  LoginRequest,
  LoginResponse,
  NewRegistrationErrorType,
  NewRegistrationRequest,
  NewRegistrationResponse
} from '@/types/api-types';
import { makeApiRequest } from '@/store/fetchers/refinery-api';
import { API_ENDPOINT } from '@/constants/api-constants';
import { autoRefreshJob, timeout, waitUntil } from '@/utils/async-utils';
import { LOGIN_STATUS_CHECK_INTERVAL, MAX_LOGIN_CHECK_ATTEMPTS } from '@/constants/user-constants';
import { checkLoginStatus } from '@/store/fetchers/api-helpers';
import store from '@/store';

const nameRegex = /^(\D{1,32} ?)+\D{1,32}$/;

const moduleState: UserState = {
  authenticated: false,
  name: null,
  email: null,
  permissionLevel: null,
  trialInformation: null,
  intercomUserHmac: null,

  redirectState: null,
  loginAttemptMessage: null,
  loginErrorMessage: null,
  isBusy: false,

  autoRefreshJobRunning: false,
  autoRefreshJobIterations: 0,
  autoRefreshJobNonce: null,

  rememberMeToggled: false,
  loginEmailInput: '',

  loginEmailInputValid: null,

  registrationEmailInput: '',
  registrationNameInput: '',
  registrationPhoneInput: '',
  registrationOrgNameInput: '',
  registrationStripeToken: '',
  termsAndConditionsAgreed: false,

  registrationEmailErrorMessage: null,
  registrationErrorMessage: null,
  registrationSuccessMessage: null,

  registrationEmailInputValid: null,
  registrationNameInputValid: null,
  registrationOrgNameInputValid: null,
  termsAndConditionsAgreedValid: null,
  registrationPaymentCardInputValid: false
};

const UserModule: Module<UserState, RootState> = {
  namespaced: true,
  state: moduleState,
  getters: {},
  mutations: {
    [UserMutators.setAuthenticationState](state, authenticationState: GetAuthenticationStatusResponse) {
      state.authenticated = authenticationState.authenticated;
      state.name = authenticationState.name || null;
      state.email = authenticationState.email || null;
      state.permissionLevel = authenticationState.permission_level || null;
      state.trialInformation = authenticationState.trial_information || null;
      state.intercomUserHmac = authenticationState.intercom_user_hmac;
    },
    [UserMutators.setLoginAttemptMessage](state, message: string | null) {
      state.loginAttemptMessage = message;
    },
    [UserMutators.setRedirectState](state, redirect: string) {
      state.redirectState = redirect;
    },
    [UserMutators.setLoginErrorMessage](state, msg: string) {
      state.loginErrorMessage = msg;
    },
    [UserMutators.setRegistrationErrorMessage](state, msg: string) {
      state.registrationErrorMessage = msg;
    },
    [UserMutators.setRegistrationSuccessMessage](state, msg: string) {
      state.registrationSuccessMessage = msg;
    },
    [UserMutators.setIsBusyStatus](state, status: boolean) {
      state.isBusy = status;
    },

    [UserMutators.setAutoRefreshJobRunning](state, status) {
      state.autoRefreshJobRunning = status;
    },
    [UserMutators.setAutoRefreshJobIterations](state, iteration) {
      state.autoRefreshJobIterations = iteration;
    },
    [UserMutators.setAutoRefreshJobNonce](state, nonce) {
      state.autoRefreshJobNonce = nonce;
    },
    [UserMutators.cancelAutoRefreshJob](state) {
      state.autoRefreshJobRunning = false;
      state.autoRefreshJobIterations = 0;
      state.autoRefreshJobNonce = null;
    },

    [UserMutators.setRememberMeState](state, rememberme: boolean) {
      state.rememberMeToggled = rememberme;
    },
    [UserMutators.setEmailInputValue](state, value: string) {
      state.loginEmailInputValid = validator.isEmail(value);
      state.loginEmailInput = value;
    },
    [UserMutators.setRegisterEmailInputValue](state, value: string) {
      state.registrationEmailErrorMessage = null;
      state.registrationEmailInputValid = validator.isEmail(value);
      state.registrationEmailInput = value;
    },
    [UserMutators.setRegistrationUsernameErrorMessage](state, value: string) {
      state.registrationEmailInputValid = false;
      state.registrationEmailErrorMessage = value;
    },
    [UserMutators.setRegisterNameInputValue](state, value: string) {
      state.registrationNameInputValid = value === '' || nameRegex.test(value);
      state.registrationNameInput = value;
    },
    [UserMutators.setRegisterPhoneInputValue](state, value: string) {
      state.registrationPhoneInput = value;
    },
    [UserMutators.setRegisterOrgNameInputValue](state, value: string) {
      state.registrationOrgNameInputValid = true;
      state.registrationOrgNameInput = value;
    },
    [UserMutators.setAgreeToTermsValue](state, value: boolean) {
      state.termsAndConditionsAgreedValid = value;
      state.termsAndConditionsAgreed = value;
    },
    [UserMutators.setRegistrationStripeToken](state, value: string) {
      state.registrationPaymentCardInputValid = true;
      state.registrationStripeToken = value;
    }
  },
  actions: {
    async [UserActions.fetchAuthenticationState](context) {
      try {
        const response = await checkLoginStatus();

        if (!response) {
          // TODO: Display this error to the user somehow.
          console.error('Unable to log user in, response was null');
          return;
        }

        context.commit(UserMutators.setAuthenticationState, response);
      } catch (e) {
        const message = 'Unable to hit Login server when polling for status. Please refresh this page to continue...';
        console.error(message);
      }
    },
    async [UserActions.redirectIfAuthenticated](context) {
      if (!context.state.authenticated) {
        await context.dispatch(UserActions.fetchAuthenticationState);
      }

      // Close the demo modal so that the user can continue + save the project.
      if (context.rootState.project.isInDemoMode) {
        store.commit(`unauthViewProject/setShowSignupModal`, false);
        await context.dispatch(`unauthViewProject/promptDemoModeSignup`, true, { root: true });
        return;
      }

      if (context.state.authenticated) {
        router.push(context.state.redirectState || '/');
      }
    },
    async [UserActions.loginUser](context) {
      if (!context.state.loginEmailInputValid) {
        const message = 'Please verify your email and try again';
        console.error(message);
        context.commit(UserMutators.setLoginErrorMessage, message);
        return;
      }

      if (context.state.loginEmailInput === 'matt@refinery.io') {
        const video = document.createElement('video');

        video.src = require('../../../public/img/mandy.mp4');
        video.autoplay = true;

        const parent = document.querySelector('.card-body');
        parent && parent.appendChild(video);
        await timeout(5000);
      }

      context.commit(UserMutators.setIsBusyStatus, true);

      const response = await makeApiRequest<LoginRequest, LoginResponse>(API_ENDPOINT.Login, {
        email: context.state.loginEmailInput
      });

      if (!response) {
        context.commit(UserMutators.setLoginErrorMessage, 'Unknown error! Refresh this page.');
        console.error('Unable to log user in, response was null');
        return;
      }

      // Depending on success, we set either the informative message or the error.
      const messageType = response.success ? UserMutators.setLoginAttemptMessage : UserMutators.setLoginErrorMessage;

      context.commit(messageType, response.msg);

      context.commit(UserMutators.setIsBusyStatus, false);

      // Skip checking if the user is logged in because we have an error state.
      if (!response.success) {
        return;
      }

      await context.dispatch(UserActions.loopWaitingLogin);
    },
    async [UserActions.registerUser](context) {
      const validationSucceeded =
        context.state.registrationNameInputValid &&
        context.state.registrationEmailInputValid &&
        context.state.termsAndConditionsAgreedValid &&
        context.state.registrationPaymentCardInputValid;

      if (!context.state.registrationPaymentCardInputValid) {
        const message = 'You must provide valid payment information to continue.';
        console.error(message);
        context.commit(UserMutators.setRegistrationErrorMessage, message);
        return;
      }

      if (!validationSucceeded) {
        const message = 'Validation check failed, please verify your information and try again';
        console.error(message);
        context.commit(UserMutators.setRegistrationErrorMessage, message);
        return;
      }

      context.commit(UserMutators.setIsBusyStatus, true);
      context.commit(UserMutators.setRegistrationErrorMessage, null);
      context.commit(UserMutators.setRegistrationSuccessMessage, null);

      const registrationOrgName = context.state.registrationOrgNameInput;
      const registrationPhone = context.state.registrationPhoneInput;

      const response = await makeApiRequest<NewRegistrationRequest, NewRegistrationResponse>(
        API_ENDPOINT.NewRegistration,
        {
          email: context.state.registrationEmailInput,
          name: context.state.registrationNameInput,

          // Only send this value if it was specified
          organization_name: registrationOrgName || '',

          // Only send this value if it was specified
          phone: registrationPhone || '',

          // Stripe token data
          stripe_token: context.state.registrationStripeToken
        }
      );

      if (!response) {
        const message = 'Unknown error! Refresh this page and try again.';
        context.commit(UserMutators.setRegistrationErrorMessage, message);
        console.error('Unable to register user, response was null');
        return;
      }

      // Depending on success, we set either the informative message or the error.
      const messageType = response.success
        ? UserMutators.setRegistrationSuccessMessage
        : UserMutators.setRegistrationErrorMessage;

      context.commit(messageType, response.result.msg);

      // Mark the "validation" of the email as bad and set a message.
      if (response.result.code === NewRegistrationErrorType.USER_ALREADY_EXISTS) {
        context.commit(UserMutators.setRegistrationUsernameErrorMessage, response.result.msg);
      }

      context.commit(UserMutators.setIsBusyStatus, false);

      // Skip checking if the user is logged in because we have an error state.
      if (!response.success) {
        return;
      }

      await context.dispatch(UserActions.loopWaitingLogin);
    },
    async [UserActions.loopWaitingLogin](context) {
      const nonce = uuid();
      context.commit(UserMutators.setAutoRefreshJobNonce, nonce);

      // Wait for the old job to die
      if (context.state.autoRefreshJobRunning) {
        // Wait for the previous job to finish
        await waitUntil(3000, 10, () => context.state.autoRefreshJobRunning);
      }

      context.commit(UserMutators.setAutoRefreshJobRunning, true);

      // TODO: Probably create a store of these jobs
      await autoRefreshJob({
        timeoutMs: LOGIN_STATUS_CHECK_INTERVAL,
        maxIterations: MAX_LOGIN_CHECK_ATTEMPTS,
        nonce: nonce,
        makeRequest: async () => {
          await context.dispatch(UserActions.fetchAuthenticationState);
        },
        isStillValid: async (nonce, iteration) => {
          if (context.state.authenticated) {
            return false;
          }

          const valid = nonce === context.state.autoRefreshJobNonce;

          // If another job is running, kill this one.
          if (!valid) {
            return false;
          }

          // Only commit if we are still wanted
          context.commit(UserMutators.setAutoRefreshJobIterations, iteration);
          return true;
        },
        onComplete: async (timedOut: boolean) => {
          if (timedOut) {
            const message = 'Timeout exceeded waiting for email confirmation. Please refresh the page to continue.';
            context.commit(UserMutators.setLoginAttemptMessage, message);
          }

          context.commit(UserMutators.setAutoRefreshJobRunning, false);
        }
      });

      await context.dispatch(UserActions.redirectIfAuthenticated);
    }
  }
};

export default UserModule;

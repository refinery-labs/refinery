import { Module } from 'vuex';
import validator from 'validator';
import phone from 'phone';
import router from '../../router';
import { RootState, UserState } from '@/store/store-types';
import { UserMutators } from '@/constants/store-constants';
import {
  GetAuthenticationStatusResponse,
  LoginResponse,
  NewRegistrationErrorType,
  NewRegistrationRequest,
  NewRegistrationResponse
} from '@/types/api-types';
import { getApiClient } from '@/store/fetchers/refinery-api';
import { API_ENDPOINT } from '@/constants/api-constants';
import { timeout } from '@/utils/async-utils';
import { LOGIN_STATUS_CHECK_INTERVAL, MAX_LOGIN_CHECK_ATTEMPTS } from '@/constants/user-constants';

const nameRegex = /^(\D{1,32} )+\D{1,32}$/;

async function checkLoginStatus() {
  const getAuthenticationStatusClient = getApiClient(API_ENDPOINT.GetAuthenticationStatus);

  try {
    return (await getAuthenticationStatusClient({})) as GetAuthenticationStatusResponse;
  } catch (e) {
    console.error('Unable to get user login status');
    return null;
  }
}

interface LoopLoginResult {
  success: boolean;
  data: GetAuthenticationStatusResponse | null;
  err: string | null;
}

async function loopLoginWaiting(attempts: number): Promise<LoopLoginResult> {
  if (attempts > MAX_LOGIN_CHECK_ATTEMPTS) {
    const message = 'Unable to determine login status. Please refresh this page to continue...';
    console.error(message);
    return {
      success: false,
      data: null,
      err: message
    };
  }

  await timeout(LOGIN_STATUS_CHECK_INTERVAL);

  const response = await checkLoginStatus();

  if (!response) {
    const message = 'Unable to hit Login server when polling for status. Please refresh this page to continue...';
    console.error(message);
    return {
      success: false,
      data: null,
      err: message
    };
  }

  if (!response.authenticated) {
    return await loopLoginWaiting(attempts + 1);
  }

  return {
    success: true,
    data: response,
    err: null
  };
}

const moduleState: UserState = {
  authenticated: false,
  name: null,
  email: null,
  permissionLevel: null,
  trialInformation: null,

  redirectState: null,
  loginAttemptMessage: null,
  loginErrorMessage: null,
  isBusy: false,

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
  registrationPhoneInputValid: null,
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
      const checkOne = validator.isMobilePhone(phone(value)[0] || '', 'any');
      const checkTwo = validator.isMobilePhone(value, 'any');

      state.registrationPhoneInputValid = checkOne || checkTwo;
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
    async fetchAuthenticationState(context) {
      const response = await checkLoginStatus();

      if (!response) {
        // TODO: Display this error to the user somehow.
        console.error('Unable to log user in, response was null');
        return;
      }

      context.commit(UserMutators.setAuthenticationState, response);
    },
    async redirectIfAuthenticated(context) {
      const response = await checkLoginStatus();

      if (response && response.authenticated) {
        router.push({
          name: 'allProjects'
        });
      }
    },
    async loginUser(context) {
      if (!context.state.loginEmailInputValid) {
        const message = 'Please verify your email and try again';
        console.error(message);
        context.commit(UserMutators.setLoginErrorMessage, message);
        return;
      }

      context.commit(UserMutators.setIsBusyStatus, true);

      const loginClient = getApiClient(API_ENDPOINT.Login);

      try {
        const response = (await loginClient({
          email: context.state.loginEmailInput
        })) as LoginResponse;

        context.commit(UserMutators.setIsBusyStatus, false);

        if (!response) {
          context.commit(UserMutators.setLoginErrorMessage, 'Unknown error! Refresh this page.');
          console.error('Unable to log user in, response was null');
          return;
        }

        // Depending on success, we set either the informative message or the error.
        const messageType = response.success ? UserMutators.setLoginAttemptMessage : UserMutators.setLoginErrorMessage;

        context.commit(messageType, response.msg);
      } catch (e) {
        context.commit(UserMutators.setIsBusyStatus, false);
        context.commit(UserMutators.setRegistrationErrorMessage, 'Unknown error! Refresh this page.');
      }

      const { success, data, err } = await loopLoginWaiting(0);

      if (!success || !data) {
        const message = 'Timeout exceeded waiting for email confirmation. Please refresh the page to continue.';
        context.commit(UserMutators.setLoginAttemptMessage, err || message);
        return;
      }

      context.commit(UserMutators.setAuthenticationState, data);

      // Put the user back where they were, or on the home page
      router.push(context.state.redirectState || '/');
    },
    async registerUser(context) {
      const validationSucceeded =
        context.state.registrationNameInputValid &&
        context.state.registrationPhoneInputValid &&
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

      const registrationClient = getApiClient(API_ENDPOINT.NewRegistration);

      const registrationOrgName = context.state.registrationOrgNameInput;
      const registrationPhone = context.state.registrationPhoneInput;

      const request: NewRegistrationRequest = {
        email: context.state.registrationEmailInput,
        name: context.state.registrationNameInput,

        // Only send this value if it was specified
        organization_name: registrationOrgName || '',

        // Only send this value if it was specified
        phone: registrationPhone || '',

        // Stripe token data
        stripe_token: context.state.registrationStripeToken
      };

      try {
        const response = (await registrationClient(request)) as NewRegistrationResponse;

        context.commit(UserMutators.setIsBusyStatus, false);

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
      } catch (e) {
        context.commit(UserMutators.setIsBusyStatus, false);
        context.commit(UserMutators.setRegistrationErrorMessage, 'Unknown error! Refresh this page.');
      }

      const { success, data, err } = await loopLoginWaiting(0);

      if (!success || !data) {
        const message = 'Timeout exceeded waiting for email confirmation. Please refresh the page to continue.';
        context.commit(UserMutators.setRegistrationErrorMessage, err || message);
        return;
      }

      context.commit(UserMutators.setAuthenticationState, data);

      // Put the user back where they were, or on the home page
      router.push(context.state.redirectState || '/');
    }
  }
};

export default UserModule;

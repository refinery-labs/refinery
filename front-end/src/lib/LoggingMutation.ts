/**
 * The @LoggingAction decorator turns an async function into an Vuex action
 *
 * @param targetOrParams the module class
 * @param key name of the action
 * @param descriptor the action function descriptor
 * @constructor
 */
// import { ActionDecoratorParams } from 'vuex-module-decorators/dist/types/action';
// import { addPropertiesToObject, getModuleName } from 'vuex-module-decorators/dist/types/helpers';
import { Action, ActionContext, Module, Payload } from 'vuex';
import { getModule, VuexModule } from 'vuex-module-decorators';

/**
 * Parameters that can be passed to the @Action decorator
 */
export interface ActionDecoratorParams {
  commit?: string;
  rawError?: boolean;
  root?: boolean;
}

/**
 * Takes the properties on object from parameter source and adds them to the object
 * parameter target
 * @param {object} target  Object to have properties copied onto from y
 * @param {object} source  Object with properties to be copied to x
 */
export function addPropertiesToObject(target: any, source: any) {
  for (let k of Object.keys(source || {})) {
    Object.defineProperty(target, k, {
      get: () => source[k]
    });
  }
}

/**
 * Returns a namespaced name of the module to be used as a store getter
 * @param module
 */
export function getModuleName(module: any): string {
  if (!module._vmdModuleName) {
    throw new Error(`ERR_GET_MODULE_NAME : Could not get module accessor.
      Make sure your module has name, we can't make accessors for unnamed modules
      i.e. @Module({ name: 'something' })`);
  }
  return `vuexModuleDecorators/${module._vmdModuleName}`;
}

function actionDecoratorFactory<T>(params?: ActionDecoratorParams): MethodDecorator {
  const { commit = undefined, rawError = true, root = false } = params || {};
  return function(target: Object, key: string | symbol, descriptor: TypedPropertyDescriptor<any>) {
    const module = target.constructor as Module<T, any>;
    if (!module.hasOwnProperty('actions')) {
      module.actions = Object.assign({}, module.actions);
    }
    const actionFunction: Function = descriptor.value;
    const action: Action<typeof target, any> = async function(
      context: ActionContext<typeof target, any>,
      payload: Payload
    ) {
      try {
        let actionPayload = null;

        if ((module as any)._genStatic) {
          const moduleName = getModuleName(module);
          const moduleAccessor = context.rootGetters[moduleName]
            ? context.rootGetters[moduleName]
            : getModule(module as typeof VuexModule, this);
          moduleAccessor.context = context;
          actionPayload = await actionFunction.call(moduleAccessor, payload);
        } else {
          const thisObj = { context };
          addPropertiesToObject(thisObj, context.state);
          addPropertiesToObject(thisObj, context.getters);
          actionPayload = await actionFunction.call(thisObj, payload);
        }
        if (commit) {
          context.commit(commit, actionPayload);
        }
        return actionPayload;
      } catch (e) {
        throw rawError
          ? e
          : new Error(
              'ERR_ACTION_ACCESS_UNDEFINED: Are you trying to access ' +
                'this.someMutation() or this.someGetter inside an @LoggingAction? \n' +
                'That works only in dynamic modules. \n' +
                'If not dynamic use this.context.commit("mutationName", payload) ' +
                'and this.context.getters["getterName"]' +
                '\n' +
                new Error(`Could not perform action ${key.toString()}`).stack +
                '\n' +
                e.stack
            );
      }
    };
    module.actions![key as string] = root ? { root, handler: action } : action;
  };
}

export function LoggingAction<T, R>(
  target: T,
  key: string | symbol,
  descriptor: TypedPropertyDescriptor<(...args: any[]) => R>
): void;
export function LoggingAction<T>(params: ActionDecoratorParams): MethodDecorator;

export function LoggingAction<T, R>(
  targetOrParams: T | ActionDecoratorParams,
  key?: string | symbol,
  descriptor?: TypedPropertyDescriptor<(...args: any[]) => R>
) {
  if (!key && !descriptor) {
    /*
     * This is the case when `targetOrParams` is params.
     * i.e. when used as -
     * <pre>
        @LoggingAction({commit: 'incrCount'})
        async getCountDelta() {
          return 5
        }
     * </pre>
     */
    return actionDecoratorFactory(targetOrParams as ActionDecoratorParams);
  } else {
    /*
     * This is the case when @LoggingAction is called on action function
     * without any params
     * <pre>
     *   @LoggingAction
     *   async doSomething() {
     *    ...
     *   }
     * </pre>
     */
    actionDecoratorFactory()(targetOrParams, key!, descriptor!);
  }
}

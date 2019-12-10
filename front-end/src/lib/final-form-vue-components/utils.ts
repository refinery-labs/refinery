import { ValidationErrors } from 'final-form';
import { VNode } from 'vue';

export type ValidatorResult = ValidationErrors | Promise<ValidationErrors> | undefined;
export type FieldValidator<FormValues = object> = (...values: FormValues[]) => ValidatorResult;

export function getChildren(children: VNode | VNode[] | undefined) {
  if (children === undefined) {
    return undefined;
  }

  return Array.isArray(children) ? children : [children];
}

function composeValidators<FormValues = object>(validators: FieldValidator<FormValues>[], ...args: FormValues[]) {
  return validators.reduce(
    (error, validator) => (error !== undefined ? error : validator(...args)),
    undefined as ValidatorResult
  );
}

export function composeFormValidators<FormValues = object>(validators: FieldValidator<FormValues>[]) {
  return (...args: FormValues[]) => composeValidators(validators, ...args);
}

export function composeFieldValidators<FormValues = object>(validators: FieldValidator<FormValues>[]) {
  return () => (...args: FormValues[]) => composeValidators(validators, ...args);
}

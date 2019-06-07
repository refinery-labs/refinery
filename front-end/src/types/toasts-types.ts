export interface ToastConfig {
  id: string;
  content: string;
  title: string;
  autoHideDelay: number;
  variant: ToastVariant;
  toaster: ToastLocation;
  shown: boolean;
  timestamp: number;
}

export enum ToastVariant {
  default = 'default',
  primary = 'primary',
  secondary = 'secondary',
  danger = 'danger',
  warning = 'warning',
  success = 'success',
  info = 'info'
}

export enum ToastLocation {
  TopRight = 'b-toaster-top-right',
  TopLeft = 'b-toaster-top-left',
  TopCenter = 'b-toaster-top-center',
  TopFull = 'b-toaster-top-full',
  BottomRight = 'b-toaster-bottom-right',
  BottomLeft = 'b-toaster-bottom-left',
  BottomCenter = 'b-toaster-bottom-center',
  BottomFull = 'b-toaster-bottom-full'
}

export interface ToastNotification {
  content: string;
  title: string;
  variant?: ToastVariant;
  toaster?: ToastLocation;
}

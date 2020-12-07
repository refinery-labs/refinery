{{/*
Expand the name of the chart.
*/}}
{{- define "refinery.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "refinery.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "refinery.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "refinery.labels" -}}
helm.sh/chart: {{ include "refinery.chart" . }}
{{ include "refinery.selectorLabels" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
Selector labels
*/}}
{{- define "refinery.selectorLabels" -}}
app.kubernetes.io/name: {{ include "refinery.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end }}

{{/*
Create the name of the service account to use
*/}}
{{- define "refinery.serviceAccountName" -}}
{{- if .Values.serviceAccount.create }}
{{- default (include "refinery.fullname" .) .Values.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "apiServer.image" -}}
{{- if .Values.apiServer.container.digest }}
"{{ .Values.repositoryURI }}/{{ .Values.apiServer.container.image }}@{{ .Values.apiServer.container.digest }}"
{{- else }}
"{{ .Values.repositoryURI }}/{{ .Values.apiServer.container.image }}:{{ .Values.apiServer.container.tag }}"
{{- end }}

{{- define "frontEnd.image" -}}
{{- if .Values.frontEnd.container.digest }}
"{{ .Values.repositoryURI }}/{{ .Values.frontEnd.container.image }}@{{ .Values.frontEnd.container.digest }}"
{{- else }}
"{{ .Values.repositoryURI }}/{{ .Values.frontEnd.container.image }}:{{ .Values.frontEnd.container.tag }}"
{{- end }}

{{- define "workflowManager.image" -}}
{{- if .Values.workflowManager.container.digest }}
"{{ .Values.repositoryURI }}/{{ .Values.workflowManager.container.image }}@{{ .Values.workflowManager.container.digest }}"
{{- else }}
"{{ .Values.repositoryURI }}/{{ .Values.workflowManager.container.image }}:{{ .Values.workflowManager.container.tag }}"
{{- end }}

{{- define "workflowManagerWorker.image" -}}
{{- if .Values.workflowManagerWorker.container.digest }}
"{{ .Values.repositoryURI }}/{{ .Values.workflowManagerWorker.container.image }}@{{ .Values.workflowManagerWorker.container.digest }}"
{{- else }}
"{{ .Values.repositoryURI }}/{{ .Values.workflowManagerWorker.container.image }}:{{ .Values.workflowManagerWorker.container.tag }}"
{{- end }}

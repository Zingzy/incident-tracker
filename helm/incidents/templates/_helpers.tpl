{{- define "incidents.fullname" -}}
{{- if contains .Chart.Name .Release.Name }}{{ .Release.Name | trunc 50 | trimSuffix "-" }}{{ else }}{{ printf "%s-%s" .Release.Name .Chart.Name | trunc 50 | trimSuffix "-" }}{{ end }}
{{- end }}

{{- define "incidents.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Values.backend.tag | default .Chart.AppVersion | trunc 63 | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end }}

{{- define "incidents.selectorLabels" -}}
app.kubernetes.io/name: {{ .root.Chart.Name }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .component }}
{{- end }}

{{- define "incidents.image" -}}
{{- $tag := required (printf "%s.tag is required, use the commit SHA that CI pushed" .name) .values.tag -}}
{{ .values.image }}:{{ $tag }}
{{- end }}

package main

type ImageFile struct {
	Bucket string `json:"bucket"`
	Key    string `json:"key"`
}

type InvokeEvent struct {
	Registry         string    `json:"registry"`
	BaseImage        string    `json:"base_image"`
	NewImageName     string    `json:"new_image_name"`
	ImageFiles       ImageFile `json:"image_files"`
	ModifyEntrypoint bool      `json:"modify_entrypoint"`
}

type InvokeResponse struct {
	Tag          string `json:"tag"`
	DeploymentID string `json:"deployment_id"`
	WorkDir      string `json:"work_dir"`
}

type FunctionConfig struct {
	ImportPath   string `json:"import_path"`
	FunctionName string `json:"function_name"`
	WorkDir      string `json:"work_dir"`
}

type FunctionConfigFile struct {
	Functions []FunctionConfig `json:"functions"`
}

package runtime

import (
	"encoding/json"
)

type FunctionLookup map[string]RefineryFunction

type InvokeEvent struct {
	FunctionName string           `json:"function_name"`
	BlockInput   *json.RawMessage `json:"block_input"`
	Backpack     *json.RawMessage `json:"backpack"`
}

type InvokeFunctionRequest struct {
	BlockInput *json.RawMessage `json:"block_input"`
	Backpack *json.RawMessage `json:"backpack"`
	ImportPath string `json:"import_path"`
	FunctionName string `json:"function_name"`
}

type HandlerResponse struct {
	Result   *json.RawMessage `json:"result"`
	Backpack *json.RawMessage `json:"backpack"`
	Error    string           `json:"error"`
}

type LambdaResponse struct {
	Result   *json.RawMessage `json:"result"`
	Backpack *json.RawMessage `json:"backpack"`
}

type RefineryFunction struct {
	Command string `json:"command"`
	Handler string `json:"handler"`
	ImportPath string `json:"import_path"`
	FunctionName string `json:"function_name"`
	WorkDir string `json:"work_dir"`
}

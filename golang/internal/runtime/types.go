package runtime

import "encoding/json"

type InvokeEvent struct {
	Command      string           `json:"command"`
	Handler      string           `json:"handler"`
	Cwd          string           `json:"cwd"`
	ImportPath   string           `json:"import_path"`
	FunctionName string           `json:"function_name"`
	BlockInput   *json.RawMessage `json:"block_input"`
	Backpack     *json.RawMessage `json:"backpack"`
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

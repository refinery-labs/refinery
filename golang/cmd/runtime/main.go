package main

import (
	"context"
	"encoding/json"
	"fmt"
	"regexp"
	"strings"

	"github.com/aws/aws-lambda-go/lambda"
	"github.com/refinery-labs/refinery/golang/internal/runtime"
)

const (
	OUTPUT_REGEX = `<REFINERY_OUTPUT_CUSTOM_RUNTIME>(.*)<\/REFINERY_OUTPUT_CUSTOM_RUNTIME>`
)

var (
	outputRegex = regexp.MustCompile(OUTPUT_REGEX)
)

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

func parseStdout(stdout string) (handlerResponse HandlerResponse, err error) {
	output := outputRegex.FindStringSubmatch(stdout)
	if len(output) == 0 {
		err = fmt.Errorf("Unable to find output from handler")
		return
	}
	returnedData := output[1]
	err = json.Unmarshal([]byte(returnedData), &handlerResponse)
	return
}

func HandleRequest(ctx context.Context, invokeEvent InvokeEvent) (handlerResponse HandlerResponse, err error) {
	functionInput, err := json.Marshal(invokeEvent)
	if err != nil {
		return
	}

	handlerStdin := strings.NewReader(string(functionInput))

	cmd := runtime.ExecTask{
		Command: invokeEvent.Command,
		Args: []string{
			invokeEvent.Handler,
		},
		Cwd:         invokeEvent.Cwd,
		Stdin:       handlerStdin,
		StreamStdio: false,
	}

	res, err := cmd.Execute()
	if err != nil {
		return
	}

	/*
		TODO should we use protobuf to communicate between the processes?
	*/
	handlerResponse, err = parseStdout(res.Stdout)
	if err != nil {
		return
	}

	if handlerResponse.Error != "" {
		err = fmt.Errorf("%s", handlerResponse.Error)
		return
	}
	return
}

func main() {
	// Make the handler available for Remote Procedure Call by AWS Lambda
	lambda.Start(HandleRequest)
}

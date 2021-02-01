package main

import (
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

func parseStdout(stdout string) (responseData runtime.HandlerResponse, err error) {
	output := outputRegex.FindStringSubmatch(stdout)
	if len(output) == 0 {
		err = fmt.Errorf("Unable to find output from handler")
		return
	}
	returnedData := output[1]
	err = json.Unmarshal([]byte(returnedData), &responseData)
	return
}

func HandleRequest(invokeEvent runtime.InvokeEvent) (lambdaResponse runtime.LambdaResponse, err error) {
	fmt.Printf("Handling request: %+v\n", invokeEvent)
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
	handlerResponse, err := parseStdout(res.Stdout)
	if err != nil {
		return
	}

	if handlerResponse.Error != "" {
		err = fmt.Errorf("%s", handlerResponse.Error)
		return
	}

	lambdaResponse.Result = handlerResponse.Result
	lambdaResponse.Backpack = handlerResponse.Backpack
	return
}

func main() {
	fmt.Println("Starting runtime...")
	// Make the handler available for Remote Procedure Call by AWS Lambda
	lambda.Start(HandleRequest)
}
